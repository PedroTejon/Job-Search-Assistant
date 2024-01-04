from json import load
from re import sub
from time import sleep

from cloudscraper import create_scraper
from unidecode import unidecode

from interfaces.vagas.models import Listing
from modules.exceptions import MaxRetriesException
from modules.utils import get_company_by_name, listing_exists


def get_bearer_token():
    for cookie in cookies_json:
        if cookie['name'] == 'cactk':
            return cookie['value'].strip('"')

    return ''


with open('filters.json', 'rb') as f:
    filters = load(f)
with open('data/cookies.json', 'r', encoding='utf-8') as f:
    cookies_json = load(f)['catho']
COOKIES = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json]) + \
    '; session_id=99be0cd2-0098-4f6e-9206-b4555d5c5172'
token = get_bearer_token()
with open('data/local_storage.json', 'r', encoding='utf-8') as f:
    build_id = load(f)['catho_build_id']
queue = None


def filter_listing(title, listing_locations_ids, location_ids):
    if any(map(lambda x: x in title.split(), filters['exclude_words'])):
        return False

    if any(map(lambda x: x in title, filters['exclude_terms'])):
        return False

    if not any(int(city) in listing_locations_ids for city in location_ids['cities']):
        return False

    return True


def get_recommended_listings(location_ids):
    listing_id = ''
    for _ in range(500):
        sleep(0.5)
        session = create_scraper(browser={
            'browser': 'chrome',
            'platform': 'windows',
            'mobile': False
        })

        headers = {
            'accept': '*/*',
            'accept-language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'authorization': f'Bearer {token}',
            'cache-control': 'no-cache',
            'cookie': COOKIES,
            'lasteventtype': None,
            'lastjobid': None,
            'pragma': 'no-cache',
            'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
            'sec-ch-ua-mobile': '?0',
            'sec-ch-ua-platform': '"Windows"',
            'sec-fetch-dest': 'empty',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-site',
            'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'
        }
        if listing_id:
            headers['lasteventtype'] = 'discard'
            headers['lastjobid'] = str(listing_id)
        else:
            headers['lasteventtype'] = None
            headers['lastjobid'] = None

        tries = 1
        while tries <= 3:
            response = session.get(
                'https://seguro.catho.com.br/area-candidato/api/suggested-job', headers=headers)

            if response.status_code in [200, 204]:
                break
            tries += 1
            if tries > 3:
                raise MaxRetriesException

        if response.status_code == 204:
            break

        content = response.json()['data']
        listing_id = content['id']
        if not listing_exists(listing_id):
            listing_resp = session.get(f'https://www.catho.com.br/vagas/_next/data/{build_id}/sugestao/{listing_id}.json?origem_apply=sugestao-de-vagas&entrada_apply=direto&slug={listing_id}', headers={
                'accept': '*/*',
                'accept-language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'cache-control': 'no-cache',
                'cookie': COOKIES,
                'pragma': 'no-cache',
                'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
                'sec-ch-ua-mobile': '?0',
                'sec-ch-ua-platform': '"Windows"',
                'sec-fetch-dest': 'empty',
                'sec-fetch-mode': 'cors',
                'sec-fetch-site': 'same-site',
                'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'
            })

            listing_resp = listing_resp.json()['pageProps']

            listing_details = listing_resp['jobAdData']

            if filter_listing(sub(r'[\[\]\(\),./\\| ]+', ' ', unidecode(listing_details['titulo']).lower()), [listing['cidadeId'] for listing in listing_details['vagas']], location_ids):
                listing = Listing()
                listing.title = listing_details['titulo']
                listing.description = listing_details['descricao']
                listing.location = [city['cidade'] for city in listing_details['vagas'] if str(city['cidadeId']) in location_ids['cities']][0]
                listing.publication_date = listing_details['dataAtualizacao']
                listing.platform = 'Catho'
                listing.platform_id = listing_id
                if listing_details['aggregated_job']['aggregated_job']:
                    listing.application_url = listing_details['aggregated_job']['apply_url']
                else:
                    listing.application_url = f'https://www.catho.com.br/vagas/sugestao/{listing_id}'

                listing.applies = session.get(f'https://www.catho.com.br/anuncios/api/rank-position/{listing_id}/4740666336240438', headers={
                    'accept': '*/*',
                    'accept-language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                    'cache-control': 'no-cache',
                    'cookie': COOKIES,
                    'pragma': 'no-cache',
                    'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
                    'sec-ch-ua-mobile': '?0',
                    'sec-ch-ua-platform': '"Windows"',
                    'sec-fetch-dest': 'empty',
                    'sec-fetch-mode': 'cors',
                    'sec-fetch-site': 'same-site',
                    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'
                }).json()['balance']

                company_name = listing_details['contratante']['nome'] if not listing_details[
                    'contratante']['confidencial'] else 'Confidencial'
                if (company := get_company_by_name(company_name, 'catho')).platforms['catho']['name'] is None:
                    company.platforms['catho']['name'] = company_name
                    company.platforms['catho']['id'] = listing_details['empId'] if not listing_details['contratante']['confidencial'] else 'Confidencial'
                    if not company.employee_count and not listing_details['contratante']['confidencial']:
                        company.employee_count = listing_resp['hirer']['numberOfEmployees']
                    company.save()

                listing.company = company
                listing.company_name = company_name
                listing.save()

                queue.put(1)


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
        'accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
        'accept-language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
        'cache-control': 'no-cache',
        'pragma': 'no-cache',
        'sec-ch-ua': '"Not_A Brand";v="8", "Chromium";v="120", "Microsoft Edge";v="120"',
        'sec-ch-ua-mobile': '?0',
        'sec-ch-ua-platform': '"Windows"',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-site',
        'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0'
    }

    for city in filters['cities']:
        tries = 1
        while tries <= 3:
            response = session.get(
                f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={city}', headers=request_headers)

            if response.status_code == 200:
                value = list(filter(
                    lambda entry, city=city: entry['name'] == city and entry['type'] == 'city', response.json()['data']))
                if value:
                    location_ids['cities'].append(value[0]['id'])
                break
            tries += 1
            if tries > 3:
                raise MaxRetriesException

        sleep(0.2)

    for state in filters['states']:
        tries = 1
        while tries <= 3:
            response = session.get(
                f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={state}', headers=request_headers)

            if response.status_code == 200:
                value = list(filter(
                    lambda entry, state=state: entry['name'] == state and entry['type'] == 'state', response.json()['data']))
                if value:
                    location_ids['states'].append(value[0]['id'])
                break
            tries += 1
            if tries > 3:
                raise MaxRetriesException

        sleep(0.2)

    for country in filters['countries']:
        tries = 1
        while tries <= 3:
            response = session.get(
                f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={country}', headers=request_headers)

            if response.status_code == 200:
                value = list(filter(
                    lambda entry, country=country: entry['name'] == country and entry['type'] == 'country', response.json()['data']))
                if value:
                    location_ids['countries'].append(value[0]['id'])
                break
            tries += 1
            if tries > 3:
                raise MaxRetriesException

        sleep(0.2)

    return location_ids


def get_jobs(curr_queue):
    global queue
    queue = curr_queue
    
    location_ids = get_location_ids()

    get_recommended_listings(location_ids)
