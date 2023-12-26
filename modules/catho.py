from json import load
from time import sleep
from re import sub
from unidecode import unidecode
from cloudscraper import create_scraper
from modules.utils import listing_exists, get_company_by_name
from interfaces.vagas_interface.models import Listing

filters = load(open('filters.json', 'r', encoding='utf-8'))


def filter_listing(title, listing_locations_ids, location_ids):
    if any(map(lambda x: x in title.split(), filters['exclude_words'])):
        return False

    if any(map(lambda x: x in title, filters['exclude_terms'])):
        return False

    if not any([int(city) in listing_locations_ids for city in location_ids['cities']]):
        return False

    return True


def get_bearer_token(cookies):
    for cookie in cookies:
        if cookie['name'] == 'cactk':
            return cookie['value'].strip('"')


def get_recommended_listings(location_ids):
    cookies_json = load(
        open('data/cookies.json', 'r', encoding='utf-8'))['catho']
    cookies = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json]
                       ) + '; session_id=99be0cd2-0098-4f6e-9206-b4555d5c5172'
    token = get_bearer_token(cookies_json)

    listing_id = ''
    for _ in range(500):
        sleep(0.5)
        session = create_scraper(browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        })

        headers = {
            "accept": "*/*",
            "accept-language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "authorization": f"Bearer {token}",
            "cache-control": "no-cache",
            "cookie": cookies,
            "pragma": "no-cache",
            "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Microsoft Edge\";v=\"120\"",
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": "\"Windows\"",
            "sec-fetch-dest": "empty",
            "sec-fetch-mode": "cors",
            "sec-fetch-site": "same-site",
            "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
        }
        if listing_id:
            headers['lasteventtype'] = 'discard'
            headers['lastjobid'] = str(listing_id)

        while tries := 1:
            response = session.get(
                'https://seguro.catho.com.br/area-candidato/api/suggested-job', headers=headers)

            if response.status_code in [200, 204]:
                break
            elif tries > 3:
                raise Exception(
                    'MaxRetriesError: possible error in authentication/cookies or request body and requests don\'t return OK')
            tries += 1

        if response.status_code == 204:
            break

        content = response.json()['data']
        listing_id = content['id']
        if not listing_exists(listing_id):
            listing_resp = session.get(f'https://www.catho.com.br/vagas/_next/data/K0FFX3tbYixCNuDCNvnHt/sugestao/{listing_id}.json?origem_apply=sugestao-de-vagas&entrada_apply=direto&slug={listing_id}', headers={
                "accept": "*/*",
                "accept-language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                "cache-control": "no-cache",
                "cookie": cookies,
                "pragma": "no-cache",
                "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Microsoft Edge\";v=\"120\"",
                "sec-ch-ua-mobile": "?0",
                "sec-ch-ua-platform": "\"Windows\"",
                "sec-fetch-dest": "empty",
                "sec-fetch-mode": "cors",
                "sec-fetch-site": "same-origin",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
            }).json()['pageProps']

            listing_details = listing_resp['jobAdData']

            if filter_listing(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(listing_details['titulo']).lower()), [listing['cidadeId'] for listing in listing_details['vagas']], location_ids):
                listing = Listing()
                listing.title = listing_details['titulo']
                listing.description = listing_details['descricao']
                listing.publication_date = listing_details['dataAtualizacao']
                listing.platform = 'Catho'
                listing.platform_id = listing_id
                if listing_details['aggregated_job']['aggregated_job']:
                    listing.application_url = listing_details['aggregated_job']['apply_url']
                else:
                    listing.application_url = f'https://www.catho.com.br/vagas/sugestao/{listing_id}'

                listing.applies = session.get(f'https://www.catho.com.br/anuncios/api/rank-position/{listing_id}/4740666336240438', headers={
                    "accept": "*/*",
                    "accept-language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
                    "cache-control": "no-cache",
                    "cookie": cookies,
                    "pragma": "no-cache",
                    "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Microsoft Edge\";v=\"120\"",
                    "sec-ch-ua-mobile": "?0",
                    "sec-ch-ua-platform": "\"Windows\"",
                    "sec-fetch-dest": "empty",
                    "sec-fetch-mode": "cors",
                    "sec-fetch-site": "same-origin",
                    "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
                }).json()['balance']

                company_name = listing_details['contratante']['nome'] if not listing_details[
                    'contratante']['confidencial'] else 'Confidencial'
                if (company := get_company_by_name(company_name)).platforms['catho']['name'] is None:
                    company.platforms['catho']['name'] = company_name
                    company.platforms['catho']['id'] = listing_details['empId'] if not listing_details[
                        'contratante']['confidencial'] else 'Confidencial'
                    if not company.employee_count and not listing_details['contratante']['confidencial']:
                        company.employee_count = listing_resp['hirer']['numberOfEmployees']
                    company.save()

                listing.company = company
                listing.save()


def get_location_ids() -> dict:
    location_ids = {
        'cities': [],
        'states': [],
        'countries': []
    }

    session = create_scraper(browser={
        'browser': 'chrome',
        'platform': 'windows',
        'mobile': False
    })
    request_headers = {
        "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "accept-language": "pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
        "cache-control": "no-cache",
        "pragma": "no-cache",
        "sec-ch-ua": "\"Not_A Brand\";v=\"8\", \"Chromium\";v=\"120\", \"Microsoft Edge\";v=\"120\"",
        "sec-ch-ua-mobile": "?0",
        "sec-ch-ua-platform": "\"Windows\"",
        "sec-fetch-dest": "document",
        "sec-fetch-mode": "navigate",
        "sec-fetch-site": "none",
        "sec-fetch-user": "?1",
        "upgrade-insecure-requests": "1",
        "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0"
    }

    for city in filters['cities']:
        while tries := 1:
            response = session.get(
                f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={city}', headers=request_headers)

            if response.status_code == 200:
                value = list(filter(
                    lambda entry, city=city: entry['name'] == city and entry['type'] == 'city', response.json()['data']))
                if value:
                    location_ids['cities'].append(value[0]['id'])
                break
            elif tries > 3:
                raise Exception(
                    'MaxRetriesError: possible error in authentication/cookies or request body and requests don\'t return OK')
            tries += 1

        sleep(0.2)

    for state in filters['states']:
        while tries := 1:
            response = session.get(
                f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={state}', headers=request_headers)

            if response.status_code == 200:
                value = list(filter(
                    lambda entry, state=state: entry['name'] == state and entry['type'] == 'state', response.json()['data']))
                if value:
                    location_ids['states'].append(value[0]['id'])
                break
            elif tries > 3:
                raise Exception(
                    'MaxRetriesError: possible error in authentication/cookies or request body and requests don\'t return OK')
            tries += 1

        sleep(0.2)

    for country in filters['countries']:
        while tries := 1:
            response = session.get(
                f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={country}', headers=request_headers)

            if response.status_code == 200:
                value = list(filter(
                    lambda entry, country=country: entry['name'] == country and entry['type'] == 'country', response.json()['data']))
                if value:
                    location_ids['countries'].append(value[0]['id'])
                break
            elif tries > 3:
                raise Exception(
                    'MaxRetriesError: possible error in authentication/cookies or request body and requests don\'t return OK')
            tries += 1

        sleep(0.2)

    return location_ids


def get_jobs():
    location_ids = get_location_ids()

    get_recommended_listings(location_ids)
