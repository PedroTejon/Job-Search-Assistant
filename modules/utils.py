from json import dump, load
from os import listdir
from re import sub

from unidecode import unidecode

from interfaces.vagas.models import Company, Listing

if 'filters.json' not in listdir('data'):
    filters = {
        "title_exclude_words": [],
        "title_exclude_terms": [],
        "company_exclude_words": [],
        "company_exclude_terms": [],
        "cities": [],
        "states": [],
        "countries": []
    }
    dump(filters, 'data/filters.json', ensure_ascii=False)
else:
    with open('data/filters.json', 'r', encoding='utf-8') as f:
        filters = load(f)


def reload_filters():
    global filters
    with open('data/filters.json', 'r', encoding='utf-8') as f:
        filters = load(f)


def company_exists_by_id(c_id, platform) -> bool:
    if platform == 'linkedin':
        return Company.objects.filter(platforms__linkedin__id__exact=c_id).exists()
    if platform == 'glassdoor':
        return Company.objects.filter(platforms__glassdoor__id__exact=c_id).exists()
    if platform == 'catho':
        return Company.objects.filter(platforms__catho__id__exact=c_id).exists()
    if platform == 'vagas_com':
        return Company.objects.filter(platforms__vagas_com__id__exact=c_id).exists()

    return False


def get_company_by_name(c_name, platform) -> Company:
    try:
        if platform == 'linkedin':
            return Company.objects.get(platforms__linkedin__name__iexact=c_name)
        if platform == 'glassdoor':
            return Company.objects.get(platforms__glassdoor__name__iexact=c_name)
        if platform == 'catho':
            return Company.objects.get(platforms__catho__name__iexact=c_name)
        if platform == 'vagas.com':
            return Company.objects.get(platforms__vagas_com__name__iexact=c_name)

        raise Exception('InvalidPlatform: a plataforma inserida não está entre as suportadas')
    except Company.DoesNotExist:
        return Company()


def asciify_text(text):
    return sub(r'[\[\]\(\),./\\| !?#]+', ' ', unidecode(text).lower())


def listing_exists(c_id) -> bool:
    return Listing.objects.filter(platform_id__exact=c_id).exists()


def filter_listing(title, location, workplace_type, company_name) -> bool:
    if location.count(',') == 2:
        city, state, country = location.split(', ')
    elif location.count(',') == 1:
        state, country = location.split(', ')
    elif location.count(',') == 0:
        city = location.split(', ')[0]

    if workplace_type == 'Presencial/Hibrido':
        if 'city' in locals() and not any(map(lambda x: x == city, filters['cities'])):
            return False
        if 'state' in locals() and not any(map(lambda x: x == state, filters['states'])):
            return False
        if 'country' in locals() and not any(map(lambda x: x == country, filters['countries'])):
            return False

    if any(map(lambda x: x in title.split(), filters['title_exclude_words'])):
        return False

    if any(map(lambda x: x in title, filters['title_exclude_terms'])):
        return False

    if any(map(lambda x: x in company_name.split(), filters['company_exclude_words'])):
        return False

    if any(map(lambda x: x in company_name, filters['company_exclude_terms'])):
        return False

    return True
