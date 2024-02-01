from __future__ import annotations

from json import load
from os.path import split as path_split
from queue import Queue
from sys import exc_info
from typing import TYPE_CHECKING

from cloudscraper import create_scraper

from interfaces.vagas.models import Listing
from modules.exceptions import MaxRetriesError
from modules.utils import DEFAULT_HEADERS, asciify_text, get_company_by_name, listing_exists, reload_filters, sleep_r

if TYPE_CHECKING:
    from types import TracebackType


def get_bearer_token() -> str:
    for cookie in cookies_json:
        if cookie['name'] == 'cactk':
            return cookie['value'].strip('"')

    return ''


with open('data/local_storage.json', encoding='utf-8') as local_storage_f:
    build_id: str = load(local_storage_f)['catho_build_id']
with open('data/cookies.json', encoding='utf-8') as cookies_f:
    cookies_json: list[dict[str, str]] = load(cookies_f)['catho']
with open('data/filters.json', 'rb') as filters_f:
    filters: dict[str, list[str]] = load(filters_f)
token: str = get_bearer_token()
queue: Queue = Queue()
log_queue: Queue = Queue()

COOKIES: str = ';'.join([f"{cookie['name']}={cookie['value']}" for cookie in cookies_json])
MODULE_HEADERS: dict[str, str] = DEFAULT_HEADERS | {
    'accept': '*/*',
    'authorization': f'Bearer {token}',
    'cookie': COOKIES,
}


def reload_if_configs_changed() -> None:
    if log_queue.qsize() > 0:
        temp_logs = []
        for _ in range(log_queue.qsize()):
            log = log_queue.get()
            if log['type'] == 'reload_request':
                reload_filters()
            else:
                temp_logs.append(log)


def filter_listing(
    title: str, listing_locations_ids: list[int], location_ids: dict[str, list[int]], company_name: str
) -> bool:
    if any(x in title.split() for x in filters['title_exclude_words']):
        return False

    if any(x in title for x in filters['title_exclude_terms']):
        return False

    if any(x in company_name.split() for x in filters['company_exclude_words']):
        return False

    if any(x in company_name for x in filters['company_exclude_terms']):
        return False

    if not any(int(city) in listing_locations_ids for city in location_ids['cities']):
        return False

    return True


def get_recommended_listings(location_ids: dict[str, list[int]]) -> None:
    listing_id = ''
    for _ in range(500):
        sleep_r(0.5)
        session = create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})

        headers = MODULE_HEADERS
        if listing_id:
            headers['lasteventtype'] = 'discard'
            headers['lastjobid'] = str(listing_id)
        else:
            # headers['lasteventtype'] = None
            # headers['lastjobid'] = None
            headers['lasteventtype'] = ''
            headers['lastjobid'] = ''

        tries = 1
        while tries <= 3:
            response = session.get('https://seguro.catho.com.br/area-candidato/api/suggested-job', headers=headers)

            if response.status_code in {200, 204}:
                break
            tries += 1
            if tries > 3:
                raise MaxRetriesError

        if response.status_code == 204:
            break

        content = response.json()['data']
        listing_id = content['id']
        if not listing_exists(listing_id):
            listing_resp = session.get(
                f'https://www.catho.com.br/vagas/_next/data/{build_id}/sugestao/{listing_id}.json?origem_apply=sugestao-de-vagas&entrada_apply=direto&slug={listing_id}',
                headers=MODULE_HEADERS,
            )

            listing_resp = listing_resp.json()['pageProps']

            listing_details = listing_resp['jobAdData']
            company_name = (
                listing_details['contratante']['nome']
                if not listing_details['contratante']['confidencial']
                else 'Confidencial'
            )

            reload_if_configs_changed()
            listing_city_ids = [listing['cidadeId'] for listing in listing_details['vagas']]
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

                listing.applies = session.get(
                    f'https://www.catho.com.br/anuncios/api/rank-position/{listing_id}/4740666336240438',
                    headers=MODULE_HEADERS,
                ).json()['balance']

                if (company := get_company_by_name(company_name, 'catho')).platforms['catho']['name'] is None:
                    company.platforms['catho']['name'] = company_name
                    company.platforms['catho']['id'] = (
                        listing_details['empId']
                        if not listing_details['contratante']['confidencial']
                        else 'Confidencial'
                    )
                    if not company.employee_count and not listing_details['contratante']['confidencial']:
                        company.employee_count = listing_resp['hirer']['numberOfEmployees']
                    company.save()

                listing.company = company
                listing.company_name = company_name
                listing.save()

                queue.put(1)


def get_location_ids() -> dict:
    location_ids: dict[str, list[int]] = {'cities': [], 'states': [], 'countries': []}

    session = create_scraper(browser={'browser': 'chrome', 'platform': 'windows', 'mobile': False})

    for city in filters['cities']:
        tries = 1
        while tries <= 3:
            response = session.get(
                f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={city}', headers=MODULE_HEADERS
            )

            if response.status_code == 200:
                value = next(
                    (
                        entry
                        for entry in response.json()['data']
                        if asciify_text(entry['name']) == city and entry['type'] == 'city'
                    ),
                    None,
                )
                if value:
                    location_ids['cities'].append(value['id'])
                break
            tries += 1
            if tries > 3:
                raise MaxRetriesError

        sleep_r(0.5)

    for state in filters['states']:
        tries = 1
        while tries <= 3:
            response = session.get(
                f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={state}', headers=MODULE_HEADERS
            )

            if response.status_code == 200:
                value = next(
                    (
                        entry
                        for entry in response.json()['data']
                        if asciify_text(entry['name']) == state and entry['type'] == 'state'
                    ),
                    None,
                )
                if value:
                    location_ids['states'].append(value['id'])
                break
            tries += 1
            if tries > 3:
                raise MaxRetriesError

        sleep_r(0.5)

    for country in filters['countries']:
        tries = 1
        while tries <= 3:
            response = session.get(
                f'https://seguro.catho.com.br/vagas/vagas-api/location/?locationName={country}', headers=MODULE_HEADERS
            )

            if response.status_code == 200:
                value = next(
                    (
                        entry
                        for entry in response.json()['data']
                        if asciify_text(entry['name']) == country and entry['type'] == 'country'
                    ),
                    None,
                )
                if value:
                    location_ids['countries'].append(value['id'])
                break
            tries += 1
            if tries > 3:
                raise MaxRetriesError

        sleep_r(0.5)

    return location_ids


def get_jobs(curr_queue: Queue, curr_log_queue: Queue) -> None:
    global queue, log_queue
    queue = curr_queue
    log_queue = curr_log_queue

    location_ids = get_location_ids()
    try:
        get_recommended_listings(location_ids)
    except Exception:
        exc_inf: tuple = exc_info()
        exc_class: type[BaseException] = exc_inf[0]
        exc_data: TracebackType = exc_inf[2]

        if (exc_next := exc_data.tb_next) is not None:
            file_name = path_split(exc_next.tb_frame.f_code.co_filename)[1]
            while exc_data.tb_next is not None and path_split(exc_data.tb_next.tb_frame.f_code.co_filename)[1]:
                exc_data = exc_data.tb_next

        log_queue.put({
            'type': 'error',
            'exception': exc_class.__name__,
            'file_name': file_name,
            'file_line': exc_data.tb_lineno,
        })
