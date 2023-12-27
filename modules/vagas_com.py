from json import load
from re import sub
from time import sleep

from bs4 import BeautifulSoup
from cloudscraper import create_scraper
from django.utils.timezone import datetime, now, timedelta
from unidecode import unidecode

from interfaces.vagas_interface.models import Company, Listing
from modules.exceptions import MaxRetriesException
from modules.utils import filter_listing, get_company_by_name, listing_exists


def get_bearer_token():
    for cookie in cookies_json:
        if cookie['name'] == 'vagas_token_integracao':
            return cookie['value'].strip('"')

    return ''


with open('filters.json', 'rb') as f:
    filters = load(f)
with open('data/cookies.json', 'rb') as f:
    cookies_json = load(f)['vagas.com']
COOKIES = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json]) + \
    '; session_id=99be0cd2-0098-4f6e-9206-b4555d5c5172'
token = get_bearer_token()


def filter_title(title):
    title = sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(title).lower())
    if any(map(lambda x: x in title.split(), filters['exclude_words'])):
        return False

    if any(map(lambda x: x in title, filters['exclude_terms'])):
        return False

    return True


def filter_location(location, workplace_type):
    if workplace_type == 'Presencial/Hibrido' and len(filters['cities']) and not any(map(lambda x: x == location, filters['cities'])):
        return False

    return True


def get_companies_listings():
    session = create_scraper(browser={
        'browser': 'firefox',
        'platform': 'windows',
        'mobile': False
    })

    for company in filter(lambda x: x.platforms['vagas_com']['name'] not in [None, 'not_found'] and not x.checked_recently('vagas_com') and x.followed, Company.objects.all()):
        page = 1

        while True:
            sleep(0.5)
            response = session.get(
                f"https://www.vagas.com.br/empregos/{company.platforms['vagas_com']['id']}?page={page}")
            soup = BeautifulSoup(response.text, 'html.parser')

            listing_urls = [link['href'] for link in soup.find_all('a', {'class': 'link-detalhes-vaga'})
                            if not listing_exists(link['data-id-vaga']) and filter_title(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(link.get_text(strip=True)).lower()))]
            if not listing_urls:
                break

            for url in listing_urls:
                sleep(0.5)
                listing_response = session.get(
                    'https://www.vagas.com.br' + url)
                listing_soup = BeautifulSoup(
                    listing_response.text, 'html.parser')

                listing = Listing()
                listing.title = listing_soup.find(
                    'h1', {'class': 'job-shortdescription__title'}).get_text(strip=True)
                listing.location = listing_soup.find(
                    'span', {'class': 'info-localizacao'}).get_text(strip=True)
                listing.workplace_type = 'Remoto' if listing.location == '100% Home Office' else 'Presencial/Hibrido'
                if filter_location(listing.location, listing.workplace_type):
                    listing.company = company
                    listing.description = listing_soup.find('div', {'class': 'job-description__text'}).text.strip() + \
                        listing_soup.find('div', {'class': 'job-company-presentation'}).text.strip() + \
                        'Benefícios:\n' + '\n'.join([benefit.get_text(
                            strip=True) for benefit in listing_soup.find_all('span', {'class': 'benefit-label'})])
                    listing.platform_id = listing_soup.find(
                        'li', {'class': 'job-breadcrumb__item--id'}).get_text(strip=True)
                    listing.platform = 'Vagas.com'

                    data = listing_soup.find('li', {'class': 'job-breadcrumb__item--published'}).get_text(strip=True)
                    if '/' in data:
                        data = datetime.strptime(data.split()[-1], '%d/%m/%Y')
                    elif 'há' in data:
                        data = now() - timedelta(days=int(data.replace('Publicada há ', '').replace(' dias', '')))
                    elif 'ontem' in data:
                        data = now() - timedelta(days=1)
                    listing.publication_date = data.strftime('%Y-%m-%dT%H:%M:%S')
                    listing.save()

            page += 1

        company.platforms['vagas_com']['last_check'] = now().strftime('%Y-%m-%dT%H:%M:%S')
        company.save()


def get_recommended_listings():
    session = create_scraper(browser={
        'browser': 'firefox',
        'platform': 'windows',
        'mobile': False
    })

    tries = 1
    while tries <= 3:
        response = session.get('https://api-candidato.vagas.com.br/v1/perfis/paginas_personalizadas', headers={
            'accept': 'application/json, text/plain, */*',
            'accept-language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'access-control-allow-origin': '*',
            'authorization': f'Bearer {token}',
            'cache-control': 'no-cache',
            'cookie': COOKIES,
            'pragma': 'no-cache',
            'sec-ch-ua': '\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Microsoft Edge\";v=\"120\"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '\"Windows\"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'
        })

        if response.status_code == 200:
            content = response.json()
            break
        tries += 1
        if tries > 3:
            raise MaxRetriesException

    for listing in content['vagas_similares']:
        listing_title = listing['cargo']
        listing_location = listing['local_de_trabalho']
        listing_worktype = 'Remoto' if listing['modelo_local_trabalho'] == '100% Home Office' else 'Presencial/Hibrido'
        if filter_listing(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(listing_title).lower()), listing_location, listing_worktype) and not listing['exclusividade_para_pcd']:
            listing_id = listing['id']

            company_name = listing['nome_da_empresa']
            if (company := get_company_by_name(company_name)).platforms['vagas_com']['name'] is None:
                company.platforms['vagas_com']['name'] = company_name
                company.save()

            Listing(
                title=listing_title,
                location=listing_location,
                workplace_type=listing_worktype,
                company=company,
                platform_id=listing_id,
                platform='Vagas.com').save()

    for listing in content['vagas_do_dia']:
        assert False, 'not implemented'
        listing_title = listing['cargo']
        listing_location = listing['local_de_trabalho']
        listing_worktype = 'Remoto' if listing['modelo_local_trabalho'] == '100% Home Office' else 'Presencial/Hibrido'
        if filter_listing(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(listing_title).lower()), listing_location, listing_worktype) and not listing['exclusividade_para_pcd']:
            listing_id = listing['id']

            company_name = listing['nome_da_empresa']
            if (company := get_company_by_name(company_name)).platforms['vagas_com']['name'] is None:
                company.platforms['vagas_com']['name'] = company_name
                company.save()

            Listing(
                title=listing_title,
                location=listing_location,
                workplace_type=listing_worktype,
                company=company,
                platform_id=listing_id,
                platform='Vagas.com',
            ).save()


def get_followed_companies():
    session = create_scraper(browser={
        'browser': 'firefox',
        'platform': 'windows',
        'mobile': False
    })
    companies = Company.objects.all()
    for company in filter(lambda x: x.platforms['vagas_com']['id'] is None and x.followed, companies):
        for platform in company.platforms:
            if company.platforms[platform]['name'] not in [None, 'not_found']:
                sleep(0.5)
                formatted_name = sub(r'[\[\]\(\),./\\|#]+', '', unidecode(
                    company.platforms[platform]['name'])).lower().replace(' ', '-')
                response = session.get(
                    f'https://www.vagas.com.br/empregos/{formatted_name}', allow_redirects=False)

                if response.status_code == 302:
                    continue
                if response.status_code != 200:
                    break

                soup = BeautifulSoup(response.text, 'html.parser')

                company.platforms['vagas_com']['id'] = response.url.replace(
                    'https://www.vagas.com.br/empregos/', '')
                company.platforms['vagas_com']['name'] = soup.find(
                    'h1', {'class': 'titulo'}).get_text().replace('Vagas de emprego - ', '')
                break
        else:
            if company.platforms['vagas_com']['name'] in [None, 'not_found']:
                company.platforms['vagas_com']['id'] = 'not_found'
                company.platforms['vagas_com']['name'] = 'not_found'

        company.save()


def get_jobs():
    get_followed_companies()

    get_companies_listings()

    get_recommended_listings()
