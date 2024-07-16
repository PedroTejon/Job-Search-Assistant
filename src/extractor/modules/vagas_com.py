from __future__ import annotations

from json import load
from traceback import format_exc
from typing import TYPE_CHECKING

from bs4 import BeautifulSoup
from cloudscraper import CloudScraper, create_scraper  # type: ignore[import-untyped]
from django.utils.timezone import datetime, now, timedelta  # type: ignore[attr-defined]

from src.api.models import Company, Listing
from src.extractor.models import ExtractionLog
from src.extractor.modules.utils import (
    DEFAULT_HEADERS,
    asciify_text,
    filter_listing,
    get,
    get_company_by_name,
    get_filters,
    listing_exists,
    sleep_r,
)

if TYPE_CHECKING:
    from collections.abc import Iterable

    from requests import Response


def get_bearer_token() -> str:
    for cookie in cookies_json:
        if cookie['name'] == 'vagas_token_integracao':
            return cookie['value'].strip('"')

    return ''


filters = get_filters()
with open('src/data/cookies.json', 'rb') as f:
    cookies_json: list[dict[str, str]] = load(f)['vagas.com']
token = get_bearer_token()
log = None

COOKIES = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])
MODULE_HEADERS = DEFAULT_HEADERS | {
    'accept-language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'access-control-allow-origin': '*',
    'authorization': f'Bearer {token}',
    'cookie': COOKIES,
}


def filter_title(title: str, company_name: str) -> bool:
    title = asciify_text(title)

    if any(x in title.split() for x in filters.get('title_exclude_words', [])):
        return False

    if any(x in title for x in filters.get('title_exclude_terms', [])):
        return False

    if company_name is not None:
        company_name = asciify_text(company_name)
        if any(x in company_name.split() for x in filters.get('company_exclude_words', [])):
            return False

        if any(x in company_name for x in filters.get('company_exclude_terms', [])):
            return False

    return True


def filter_location(location: str, workplace_type: str) -> bool:
    return not (workplace_type == 'Presencial/Hibrido' and len(filters.get('cities', [])) and not any(x == location for x in filters.get('cities', [])))


def get_companies_listings() -> None:
    session: CloudScraper = create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    session.headers = MODULE_HEADERS

    for company in filter(  # noqa: PLR1702
        lambda x: x.platforms['vagas_com']['name'] not in {None, 'not_found'}
        and not x.checked_recently('vagas_com')
        and x.followed,
        Company.objects.all(),
    ):
        page = 1

        while True:
            sleep_r(0.5)
            response: Response = get(
                f"https://www.vagas.com.br/empregos/{company.platforms['vagas_com']['id']}?page={page}", session
            )
            soup = BeautifulSoup(response.text, 'html.parser')

            listing_urls: list[str] = [
                link['href']
                for link in soup.find_all('a', {'class': 'link-detalhes-vaga'})
                if not listing_exists(link['data-id-vaga'])
                and filter_title(link.get_text(strip=True), company.platforms['vagas_com']['name'])
            ]
            if not listing_urls:
                break

            for url in listing_urls:
                sleep_r(0.5)
                listing_response: Response = get('https://www.vagas.com.br' + url, session)
                listing_soup = BeautifulSoup(listing_response.text, 'html.parser')

                listing = Listing()

                listing_title_el = listing_soup.find('h1', {'class': 'job-shortdescription__title'})
                if listing_title_el is not None:
                    listing.title = listing_title_el.get_text(strip=True)

                listing_location_el = listing_soup.find('span', {'class': 'info-localizacao'})
                if listing_location_el is not None:
                    listing.location = listing_location_el.get_text(strip=True)

                listing.workplace_type = 'Remoto' if listing.location == '100% Home Office' else 'Presencial/Hibrido'

                # reload_if_configs_changed()
                if filter_location(listing.location, listing.workplace_type):
                    listing_platform_id_el = listing_soup.find('li', {'class': 'job-breadcrumb__item--id'})
                    if listing_platform_id_el is not None:
                        listing.platform_id = listing_platform_id_el.get_text(strip=True)

                    if listing_exists(listing.platform_id):
                        continue

                    listing.company = company
                    listing.company_name = company.platforms['vagas_com']['name']

                    listing_description_el = listing_soup.find('div', {'class': 'job-description__text'})
                    listing_company_desc_el = listing_soup.find('div', {'class': 'job-company-presentation'})
                    if listing_description_el is not None and listing_company_desc_el is not None:
                        listing.description = (
                            listing_description_el.get_text(strip=True)
                            + listing_company_desc_el.get_text(strip=True)
                            + 'Benefícios:\n'
                            + '\n'.join([
                                benefit.get_text(strip=True)
                                for benefit in listing_soup.find_all('span', {'class': 'benefit-label'})
                            ])
                        )

                    listing.platform = 'Vagas.com'

                    date_el = listing_soup.find('li', {'class': 'job-breadcrumb__item--published'})
                    if date_el is not None:
                        date_text = date_el.get_text(strip=True)

                        if '/' in date_text:
                            date = datetime.strptime(date_text.split()[-1], '%d/%m/%Y')
                        elif 'há' in date_text:
                            date = now() - timedelta(
                                days=int(date_text.replace('Publicada há ', '').replace(' dias', ''))
                            )
                        else:
                            date = now() - timedelta(days=1)
                    listing.publication_date = date.strftime('%Y-%m-%dT%H:%M:%S')

                    listing.execution_id = log.id
                    listing.save()

                    log.amount_extracted += 1
                    log.save()
            page += 1

        company.platforms['vagas_com']['last_check'] = now().strftime('%Y-%m-%dT%H:%M:%S')
        company.save()


def get_recommended_listings() -> None:
    session: CloudScraper = create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})
    session.headers = MODULE_HEADERS

    content: dict = get('https://api-candidato.vagas.com.br/v1/perfis/paginas_personalizadas', session).json()

    for listing in content['vagas_similares']:
        listing_title: str = listing['cargo']
        listing_location: str = listing['local_de_trabalho']
        listing_worktype = 'Remoto' if listing['modelo_local_trabalho'] == '100% Home Office' else 'Presencial/Hibrido'
        company_name: str = listing['nome_da_empresa']

        if filter_listing(asciify_text(listing_title), listing_location, listing_worktype, asciify_text(company_name)):
            listing_id: str = listing['id']
            if listing_exists(listing_id):
                continue

            if (company := get_company_by_name(company_name, 'vagas_com')).platforms['vagas_com']['name'] is None:
                company.platforms['vagas_com']['name'] = company_name
                company.save()

            Listing(
                title=listing_title,
                location=listing_location,
                workplace_type=listing_worktype,
                company=company,
                company_name=company_name,
                platform_id=listing_id,
                platform='Vagas.com',
                execution_id=log.id
            ).save()

            log.amount_extracted += 1
            log.save()

    for listing in content['vagas_do_dia']:
        listing_title = listing['cargo']
        listing_location = listing['local_de_trabalho']
        listing_worktype = 'Remoto' if listing['modelo_local_trabalho'] == '100% Home Office' else 'Presencial/Hibrido'
        company_name = listing['nome_da_empresa']

        if filter_listing(asciify_text(listing_title), listing_location, listing_worktype, asciify_text(company_name)):
            listing_id = listing['id']

            if (company := get_company_by_name(company_name, 'vagas_com')).platforms['vagas_com']['name'] is None:
                company.platforms['vagas_com']['name'] = company_name
                company.save()

            Listing(
                title=listing_title,
                location=listing_location,
                workplace_type=listing_worktype,
                company=company,
                company_name=company_name,
                platform_id=listing_id,
                platform='Vagas.com',
                execution_id=log.id
            ).save()

            log.amount_extracted += 1
            log.save()


def get_followed_companies() -> None:
    session: CloudScraper = create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})

    companies: Iterable[Company] = Company.objects.all()
    for company in filter(lambda x: x.platforms['vagas_com']['id'] is None and x.followed, companies):
        for platform in company.platforms:
            if company.platforms[platform]['name'] not in {None, 'not_found'}:
                sleep_r(0.5)
                formatted_name = asciify_text(company.platforms[platform]['name']).replace(' ', '-')
                response: Response = session.get(
                    f'https://www.vagas.com.br/empregos/{formatted_name}', allow_redirects=False
                )

                if response.status_code == 302:
                    continue
                if response.status_code != 200:
                    break

                soup = BeautifulSoup(response.text, 'html.parser')

                company.platforms['vagas_com']['id'] = response.url.replace('https://www.vagas.com.br/empregos/', '')
                company_name_el = soup.find('h1', {'class': 'titulo'})
                if company_name_el is not None:
                    company.platforms['vagas_com']['name'] = company_name_el.get_text().replace(
                        'Vagas de emprego - ', ''
                    )
                break
        else:
            if company.platforms['vagas_com']['name'] in {None, 'not_found'}:
                company.platforms['vagas_com']['id'] = 'not_found'
                company.platforms['vagas_com']['name'] = 'not_found'

        company.save()


def run_pipeline(execution_id) -> None:
    global log
    pipeline = [get_companies_listings, get_recommended_listings]

    log = ExtractionLog(id=execution_id, platform='Vagas.com')
    log.save()
    try:
        get_followed_companies()
        for function in pipeline:
            function()
    except Exception:
        traceback = format_exc()

        log.result = 'EXCEPTION'
        log.message = traceback
    finally:
        log.end_time = now()
        log.save()
