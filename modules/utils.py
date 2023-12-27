from json import load
from re import sub

from django.db.models import Q

from interfaces.vagas_interface.models import Company, Listing

with open('filters.json', 'r', encoding='utf-8') as f:
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


def get_company_by_name(c_name) -> Company:
    try:
        return Company.objects.get(Q(platforms__linkedin__name__iexact=c_name) | Q(platforms__glassdoor__name__iexact=c_name) | Q(platforms__catho__name__iexact=c_name))
    except Company.DoesNotExist:
        return Company()


def listing_exists(c_id) -> bool:
    return Listing.objects.filter(platform_id__exact=c_id).exists()


def filter_listing(title, location, workplace_type) -> bool:
    location = sub(
        r'\s*\(\bPresencial\b\)|\s*\(\bHíbrido\b\)|\s*\(\bRemoto\b\)', '', location)
    if location.count(',') == 2:
        city, state, country = location.split(', ')
    elif location.count(',') == 1:
        state, country = location.split(', ')
    elif location.count(',') == 0:
        city = location.split(', ')[0]

    if workplace_type == 'Presencial/Hibrido':
        if 'city' in locals() and len(filters['cities']) and not any(map(lambda x: x == city, filters['cities'])):
            return False
        if 'state' in locals() and len(filters['states']) and not any(map(lambda x: x == state, filters['states'])):
            return False
        if 'country' in locals() and len(filters['countries']) and not any(map(lambda x: x == country, filters['countries'])):
            return False

    if any(map(lambda x: x in title.split(), filters['exclude_words'])):
        return False

    if any(map(lambda x: x in title, filters['exclude_terms'])):
        return False

    return True
