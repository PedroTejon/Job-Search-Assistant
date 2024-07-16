from __future__ import annotations

from json import load
from traceback import format_exc
from typing import TYPE_CHECKING

from cloudscraper import CloudScraper, create_scraper  # type: ignore[import-untyped]
from django.utils.timezone import now

from src.api.models import Listing
from src.extractor.models import ExtractionLog
from src.extractor.modules.utils import (
    DEFAULT_HEADERS,
    asciify_text,
    get,
    get_company_by_name,
    get_filters,
    listing_exists,
    sleep_r,
)

if TYPE_CHECKING:
    from requests import Response


def get_bearer_token() -> str:
    for cookie in cookies_json:
        if cookie['name'] == 'cactk':
            return cookie['value'].strip('"')

    return ''


with open('src/data/local_storage.json', encoding='utf-8') as local_storage_f:
    build_id = load(local_storage_f)['catho_build_id']
with open('src/data/cookies.json', encoding='utf-8') as cookies_f:
    cookies_json: list[dict[str, str]] = load(cookies_f)['catho']
filters = get_filters()
token = get_bearer_token()
log = None

COOKIES = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])
MODULE_HEADERS: dict[str, str] = DEFAULT_HEADERS | {
    'accept': '*/*',
    'authorization': f'Bearer {token}',
    'cookie': COOKIES,
}


def filter_listing(
    title: str, listing_locations_ids: list[str], location_ids: dict[str, list[int]], company_name: str
) -> bool:
    if any(x in title.split() for x in filters.get('title_exclude_words', [])):
        return False

    if any(x in title for x in filters.get('title_exclude_terms', [])):
        return False

    if any(x in company_name.split() for x in filters.get('company_exclude_words', [])):
        return False

    if any(x in company_name for x in filters.get('company_exclude_terms', [])):
        return False

    return any(int(city) in listing_locations_ids for city in location_ids['cities'])


def get_recommended_listings() -> None:
    location_ids = get_location_ids()
    listing_id = ''
    for _ in range(500):
        sleep_r(0.5)
        session: CloudScraper = create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})

        headers = MODULE_HEADERS
        if listing_id:
            headers['lasteventtype'] = 'discard'
            headers['lastjobid'] = str(listing_id)
        else:
            headers['lasteventtype'] = ''
            headers['lastjobid'] = ''
        session.headers = headers

        response: Response = get('https://seguro.catho.com.br/area-candidato/api/suggested-job', session, (200, 204))
        if response.status_code == 204:
            break

        content: dict[str, str] = response.json()['data']
        listing_id = content['id']
        if not listing_exists(listing_id):
            listing_json = get(
                f'https://www.catho.com.br/vagas/_next/data/{build_id}/sugestao/{listing_id}.json?origem_apply=sugestao-de-vagas&entrada_apply=direto&slug={listing_id}',
                session,
            ).json()['pageProps']

            listing_details: dict = listing_json['jobAdData']
            company_name: str = (
                listing_details['contratante']['nome']
                if listing_details is not None and not listing_details['contratante']['confidencial']
                else 'Confidencial'
            )

            listing_city_ids: list[str] = [listing['cidadeId'] for listing in listing_details['vagas']]
            if filter_listing(
                asciify_text(listing_details['titulo']), listing_city_ids, location_ids, asciify_text(company_name)
            ):
                listing = Listing()
                listing.title = listing_details['titulo']
                listing.description = listing_details['descricao']
                listing.location = next(
                    city['cidade']
                    for city in listing_details['vagas']
                    if str(city['cidadeId']) in location_ids['cities']
                )
                listing.publication_date = listing_details['dataAtualizacao']
                listing.platform = 'Catho'
                listing.platform_id = listing_id
                if listing_details['aggregated_job']['aggregated_job']:
                    listing.application_url = listing_details['aggregated_job']['apply_url']
                else:
                    listing.application_url = f'https://www.catho.com.br/vagas/sugestao/{listing_id}'

                listing.applies = get(
                    f'https://www.catho.com.br/anuncios/api/rank-position/{listing_id}/4740666336240438',
                    session,
                ).json()['balance']

                if (company := get_company_by_name(company_name, 'catho')).platforms['catho']['name'] is None:
                    company.platforms['catho']['name'] = company_name
                    company.platforms['catho']['id'] = (
                        listing_details['empId']
                        if not listing_details['contratante']['confidencial']
                        else 'Confidencial'
                    )
                    if not company.employee_count and not listing_details['contratante']['confidencial']:
                        company.employee_count = listing_json['hirer']['numberOfEmployees']
                    company.save()

                listing.company = company
                listing.company_name = company_name
                listing.execution_id = log.id
                listing.save()

                log.amount_extracted += 1
                log.save()


def get_location_ids() -> dict:
    location_ids: dict[str, list[int]] = {'cities': [], 'states': [], 'countries': []}

    session: CloudScraper = create_scraper(
        browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False},
    )
    session.headers = MODULE_HEADERS

    for city in filters.get('cities', []):
        content: dict = get(
            f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={city}', session
        ).json()

        sleep_r(0.5)
        value: dict | None = next(
            (entry for entry in content['data'] if asciify_text(entry['name']) == city and entry['type'] == 'city'),
            None,
        )
        if value:
            location_ids['cities'].append(value['id'])

    for state in filters.get('states', []):
        content = get(f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={state}', session).json()

        sleep_r(0.5)
        value = next(
            (entry for entry in content['data'] if asciify_text(entry['name']) == state and entry['type'] == 'state'),
            None,
        )
        if value:
            location_ids['states'].append(value['id'])

    for country in filters.get('countries', []):
        content = get(f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={country}', session).json()

        sleep_r(0.5)
        value = next(
            (
                entry
                for entry in content['data']
                if asciify_text(entry['name']) == country and entry['type'] == 'country'
            ),
            None,
        )
        if value:
            location_ids['countries'].append(value['id'])

    return location_ids


def run_pipeline(execution_id) -> None:
    global log
    pipeline = [get_recommended_listings]

    log = ExtractionLog(id=execution_id, platform='Catho')
    log.save()
    try:
        for function in pipeline:
            function()
    except Exception:
        traceback = format_exc()

        log.result = 'EXCEPTION'
        log.message = traceback
    finally:
        log.end_time = now()
        log.save()
