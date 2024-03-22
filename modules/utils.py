from __future__ import annotations

from json import dump, load
from os import listdir
from random import randint
from re import sub
from time import sleep
from typing import TYPE_CHECKING

from unidecode import unidecode

from interfaces.vagas.models import Company, Listing
from modules import PLATFORM_IDS
from modules.exceptions import InvalidPlatformError, PossibleAuthError

if TYPE_CHECKING:
    from cloudscraper import CloudScraper  # type: ignore[import-untyped]
    from requests import Response

if 'filters.json' not in listdir('data'):
    filters: dict[str, list[str]] = {
        'title_exclude_words': [],
        'title_exclude_terms': [],
        'company_exclude_words': [],
        'company_exclude_terms': [],
        'cities': [],
        'states': [],
        'countries': [],
    }
    with open('data/filters.json', 'w', encoding='utf-8') as filters_f:
        dump(filters, filters_f, ensure_ascii=False)
else:
    with open('data/filters.json', encoding='utf-8') as filters_f:
        filters = load(filters_f)

DEFAULT_HEADERS = {
    'accept-language': 'pt-BR,pt;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
    'cache-control': 'no-cache',
    'pragma': 'no-cache',
    'sec-ch-ua-mobile': '?0',
    'sec-ch-ua-platform': '"Windows"',
    'sec-fetch-dest': 'empty',
    'sec-fetch-mode': 'cors',
    'sec-fetch-site': 'same-origin',
    'user-agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36 Edg/119.0.0.0',  # noqa: E501
}


def sleep_r(time: float) -> None:
    sleep(time * (1 + randint(1, 20) / 100))


def reload_filters() -> None:
    global filters
    with open('data/filters.json', encoding='utf-8') as filters_f:
        filters = load(filters_f)


def company_exists_by_id(c_id: str, platform: str) -> bool:
    if platform in PLATFORM_IDS:
        return Company.objects.filter(**{f'platforms__{platform}__id__exact': c_id}).exists()

    return False


def get_company_by_name(c_name: str, platform: str) -> Company:
    try:
        if platform in PLATFORM_IDS:
            return Company.objects.get(**{f'platforms__{platform}__id__exact': c_name})

        raise InvalidPlatformError
    except Company.DoesNotExist:
        return Company()


def get(url: str, session: CloudScraper, allowed_statuses: tuple = (200,)) -> Response:
    tries = 0
    while tries < 3:
        sleep_r(0.5)

        response: Response = session.get(url)

        if response.status_code in allowed_statuses:
            return response

        tries += 1

    raise PossibleAuthError


def post(url: str, session: CloudScraper, request_body: dict | list, allowed_statuses: tuple = (200,)) -> Response:
    tries = 0
    while tries < 3:
        sleep_r(0.5)

        response: Response = session.post(url, json=request_body)

        if response.status_code in allowed_statuses:
            return response

        tries += 1

    raise PossibleAuthError


def asciify_text(text: str) -> str:
    return sub(r'[\[\]\(\),./\\| !?#-]+', ' ', unidecode(text).lower())


def listing_exists(c_id: str) -> bool:
    return Listing.objects.filter(platform_id__exact=c_id).exists()


def filter_listing(title: str, location: str, workplace_type: str, company_name: str) -> bool:
    location = asciify_text(location)
    if location.count(',') == 2:
        city, state, country = location.split(', ')
    elif location.count(',') == 1:
        state, country = location.split(', ')
    elif location.count(',') == 0:
        city = location.split(', ')[0]

    if workplace_type == 'Presencial/Hibrido':
        if 'city' in locals() and len(filters['cities']) > 0 and not any(x == city for x in filters['cities']):
            return False
        if 'state' in locals() and len(filters['states']) > 0 and not any(x == state for x in filters['states']):
            return False
        if (
            'country' in locals()
            and len(filters['country']) > 0
            and not any(x == country for x in filters['countries'])
        ):
            return False

    if any(x in title.split() for x in filters['title_exclude_words']):
        return False

    if any(x in title for x in filters['title_exclude_terms']):
        return False

    if any(x in company_name.split() for x in filters['company_exclude_words']):
        return False

    if any(x in company_name for x in filters['company_exclude_terms']):
        return False

    return True
