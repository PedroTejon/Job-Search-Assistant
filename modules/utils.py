from __future__ import annotations

from json import dump, load
from os import listdir
from random import randint
from re import sub
from time import sleep

from unidecode import unidecode

from interfaces.vagas.models import Company, Listing
from modules.exceptions import InvalidPlatformError

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
    if platform == 'linkedin':
        return Company.objects.filter(platforms__linkedin__id__exact=c_id).exists()
    if platform == 'glassdoor':
        return Company.objects.filter(platforms__glassdoor__id__exact=c_id).exists()
    if platform == 'catho':
        return Company.objects.filter(platforms__catho__id__exact=c_id).exists()
    if platform == 'vagas_com':
        return Company.objects.filter(platforms__vagas_com__id__exact=c_id).exists()

    return False


def get_company_by_name(c_name: str, platform: str) -> Company:
    try:
        if platform == 'linkedin':
            return Company.objects.get(platforms__linkedin__name__iexact=c_name)
        if platform == 'glassdoor':
            return Company.objects.get(platforms__glassdoor__name__iexact=c_name)
        if platform == 'catho':
            return Company.objects.get(platforms__catho__name__iexact=c_name)
        if platform == 'vagas.com':
            return Company.objects.get(platforms__vagas_com__name__iexact=c_name)

        raise InvalidPlatformError
    except Company.DoesNotExist:
        return Company()


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
