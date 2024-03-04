from __future__ import annotations

from json import dump, load, loads
from queue import Queue
from re import sub
from threading import Thread
from threading import enumerate as enum_threads
from typing import TypedDict

from django.db.models import F
from django.db.models.query_utils import Q
from django.forms.models import model_to_dict
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
from numpy import arange, split
from unidecode import unidecode

from interfaces.vagas.models import Listing
from modules.catho import get_jobs as catho_extraction
from modules.glassdoor import get_jobs as glassdoor_extraction
from modules.glassdoor import get_listing_details as glassdoor_update
from modules.linkedin import get_jobs as linkedin_extraction
from modules.linkedin import get_listing_details as linkedin_update
from modules.utils import asciify_text, reload_filters
from modules.vagas_com import get_jobs as vagas_com_extraction


class PlatformThreadInfo(TypedDict):
    thread: Thread
    queue: Queue
    log_queue: Queue


threads: dict[str, PlatformThreadInfo] = {
    'linkedin': {'thread': Thread(), 'queue': Queue(), 'log_queue': Queue()},
    'glassdoor': {'thread': Thread(), 'queue': Queue(), 'log_queue': Queue()},
    'catho': {'thread': Thread(), 'queue': Queue(), 'log_queue': Queue()},
    'vagas_com': {'thread': Thread(), 'queue': Queue(), 'log_queue': Queue()},
}


def index(request: HttpRequest) -> HttpResponse:
    template = loader.get_template('vagas.html')
    page = int(request.GET.get('page', 1))
    search_query = request.GET.get('query', '')
    listing_query: list[bool] = loads(
        request.GET.get('listing', '[false, false, true, true, true, false, true, false]')
    )
    sorting_query: list[str] = loads(request.GET.get('sort', '["id", "descending"]'))
    companies_query: list[str] = loads(request.GET.get('companies', '[]'))
    cities_query: list[str] = loads(request.GET.get('cities', '[]'))
    platforms_query: list[str] = loads(request.GET.get('platforms', '[]'))

    full_query = sub(r'/vagas/\?[page=0-9]*', '', request.get_full_path()).replace('/vagas/', '')
    return HttpResponse(
        template.render(
            get_listings(
                search_query, page, listing_query, sorting_query, companies_query, cities_query, platforms_query
            )
            | {'tab_title': 'Vagas', 'full_query': full_query},
            request,
        )
    )


@csrf_exempt
def update_listing_applied_status(request: HttpRequest) -> JsonResponse:
    listing_id = request.GET.get('id')
    listing_updated_value = loads(request.GET.get('value'))  # type: ignore[arg-type]
    if listing_id:
        listing = Listing.objects.get(id__iexact=listing_id)
        listing.applied_to = listing_updated_value
        listing.save()
        return JsonResponse({'status': 200})

    return JsonResponse({'status': 404})


@csrf_exempt
def update_filter_list(request: HttpRequest) -> JsonResponse:
    filter_value = request.GET.get('filter_value', '').lower()
    filter_type = request.GET.get('filter_type')

    with open('data/filters.json', encoding='utf-8') as filters_f:
        filters = load(filters_f)

    json_body: dict[str, str | int] = {'status': 200}

    if request.method == 'POST':
        if filter in filters[filter_type]:
            return JsonResponse({'status': 409}, status=409)

        asciified_text = asciify_text(filter_value)
        filters[filter_type].append(asciified_text)
        json_body['asciified_text'] = asciified_text

        if filter_type not in {'cities', 'states', 'countries'}:
            listings = Listing.objects.all().filter(applied_to__exact=None)
            for listing in listings:
                title = asciify_text(listing.title)
                company_name = asciify_text(listing.company_name)
                if (
                    any(word in title.split() for word in filters['title_exclude_words'])
                    or any(term in title for term in filters['title_exclude_terms'])
                    or any(word in company_name.split() for word in filters['company_exclude_words'])
                    or any(term in company_name for term in filters['company_exclude_terms'])
                ) and (listing.applied_to is None):
                    listing.applied_to = False
                    listing.save()
    elif request.method == 'DELETE':
        if filter_value not in filters[filter_type]:
            return JsonResponse({'status': 404}, status=404)

        filters[filter_type].remove(filter_value)

    with open('data/filters.json', 'w', encoding='utf-8') as filters_f:
        dump(filters, filters_f, ensure_ascii=False)

    for platform in ['linkedin', 'glassdoor', 'catho', 'vagas_com']:
        if threads[platform]['thread'] is not None and threads[platform]['thread'].is_alive():
            threads[platform]['log_queue'].put({'type': 'reload_request'})

    return JsonResponse(json_body)


def update_listing_details(request: HttpRequest) -> JsonResponse:
    listing_plat_id = request.GET['id']
    listing_plat = request.GET['platform']
    listing = Listing.objects.get(platform_id=listing_plat_id)

    if listing_plat == 'LinkedIn':
        linkedin_update(listing)
    elif listing_plat == 'Glassdoor':
        glassdoor_update(listing)

    if listing.applied_to is None and listing.closed:
        listing.applied_to = False

    return JsonResponse({'status': 200, 'listing': model_to_dict(listing)})


def get_listings(
    search_queries_str: str,
    page: int,
    listing_properties: list[bool],
    sorting_properties: list[str],
    companies: list[str],
    cities: list[str],
    platforms: list[str],
) -> dict:
    with open('data/filters.json', encoding='utf-8') as f:
        filters = load(f)

    search_queries = unidecode(search_queries_str).lower().split()
    listings_query = Q()
    workplace_type_query = Q()

    # [0] = Applied, [1] = Dismissed, [2] = Not Avaliated, [3] = Local, [4] = Remote
    if not any([listing_properties[0], listing_properties[1], listing_properties[2]]):
        listing_properties[0] = False
        listing_properties[1] = False
        listing_properties[2] = True

    if not any([listing_properties[3], listing_properties[4]]):
        listing_properties[3] = True
        listing_properties[4] = True

    if listing_properties[0]:
        listings_query |= Q(applied_to__exact=True)
    if listing_properties[1]:
        listings_query |= Q(applied_to__exact=False)
    if listing_properties[2]:
        listings_query |= Q(applied_to__exact=None)
    if listing_properties[3]:
        workplace_type_query |= Q(workplace_type__iexact='presencial/hibrido')
    if listing_properties[4]:
        workplace_type_query |= Q(workplace_type__iexact='remoto')
    if listing_properties[5]:
        listings_query &= Q(company__followed=True)
    if listing_properties[6]:
        listings_query &= Q(closed=False)
    if listing_properties[7]:
        listings_query &= Q(closed=True)

    filter_query = listings_query & workplace_type_query

    sorting_query = (
        F(sorting_properties[0]).desc(nulls_last=True)
        if sorting_properties[1] == 'descending'
        else F(sorting_properties[0]).asc(nulls_last=True)
    )

    try:
        queried_listings = Listing.objects.filter(filter_query).order_by(sorting_query).values()

        if search_queries:
            queried_listings = [
                listing
                for listing in queried_listings
                for term in search_queries
                if term in unidecode(listing['title']).lower()
            ]  # type: ignore[assignment]
        if companies:
            queried_listings = [
                listing
                for listing in queried_listings
                for company in companies
                if unidecode(company).lower() in unidecode(listing['company_name']).lower()
            ]  # type: ignore[assignment]
        if cities:
            queried_listings = [
                listing
                for listing in queried_listings
                for city in cities
                if unidecode(city).lower() in unidecode(listing['location']).lower()
            ]  # type: ignore[assignment]
        if platforms:
            queried_listings = [
                listing for listing in queried_listings for platform in platforms if platform in listing['platform']
            ]  # type: ignore[assignment]

        pages = split(queried_listings, arange(50, len(queried_listings), 50))  # type: ignore[var-annotated, arg-type, call-overload]
        listings = list(list(pages)[page - 1])

        paginations = range(max(1, page - 3), min(page + 4, len(pages) + 1))
        return {
            'listings': listings,
            'page': page,
            'pages': paginations,
            'total_pages': len(pages),
            'query': search_queries_str,
            'listing_properties': listing_properties,
            'sorting_properties': sorting_properties,
            'companies': companies,
            'cities': cities,
            'platforms': platforms,
            'filters': filters,
            'listing_count': len(listings),
        }
    except IndexError:
        return {
            'listings': [],
            'page': page,
            'pages': [page],
            'total_pages': 0,
            'query': search_queries_str,
            'listing_properties': listing_properties,
            'sorting_properties': sorting_properties,
            'companies': companies,
            'cities': cities,
            'platforms': platforms,
            'filters': filters,
            'listing_count': 0,
        }


@csrf_exempt
def start_listing_extraction(request: HttpRequest) -> JsonResponse:  # noqa: ARG001
    if (
        not thread_is_running('linkedin_extraction')
        and not thread_is_running('glassdoor_extraction')
        and not thread_is_running('catho_extraction')
        and not thread_is_running('vagas_com_extraction')
    ):
        reload_filters()

        threads['linkedin']['queue'] = Queue()
        threads['linkedin']['log_queue'] = Queue()
        threads['linkedin']['thread'] = Thread(
            target=linkedin_extraction,
            name='linkedin_extraction',
            args=[threads['linkedin']['queue'], threads['linkedin']['log_queue']],
        )
        threads['linkedin']['thread'].start()

        threads['glassdoor']['queue'] = Queue()
        threads['glassdoor']['log_queue'] = Queue()
        threads['glassdoor']['thread'] = Thread(
            target=glassdoor_extraction,
            name='glassdoor_extraction',
            args=[threads['glassdoor']['queue'], threads['glassdoor']['log_queue']],
        )
        threads['glassdoor']['thread'].start()

        threads['catho']['queue'] = Queue()
        threads['catho']['log_queue'] = Queue()
        threads['catho']['thread'] = Thread(
            target=catho_extraction,
            name='catho_extraction',
            args=[threads['catho']['queue'], threads['catho']['log_queue']],
        )
        threads['catho']['thread'].start()

        threads['vagas_com']['queue'] = Queue()
        threads['vagas_com']['log_queue'] = Queue()
        threads['vagas_com']['thread'] = Thread(
            target=vagas_com_extraction,
            name='vagas_com_extraction',
            args=[threads['vagas_com']['queue'], threads['vagas_com']['log_queue']],
        )
        threads['vagas_com']['thread'].start()

        return JsonResponse({'status': 200})

    return JsonResponse({'status': 409}, status=409)


def get_listing_extraction_status(request: HttpRequest) -> JsonResponse:  # noqa: ARG001
    response_body: dict = {
        'status': 200,
        'results': {
            'linkedin': {'status': False, 'new_listings': 0},
            'glassdoor': {'status': False, 'new_listings': 0},
            'catho': {'status': False, 'new_listings': 0},
            'vagas_com': {'status': False, 'new_listings': 0},
        },
    }

    for platform in ['linkedin', 'glassdoor', 'catho', 'vagas_com']:
        if threads[platform]['queue'] is not None:
            response_body['results'][platform]['status'] = (
                threads[platform]['thread'].is_alive() if threads[platform]['thread'] is not None else False
            )
            response_body['results'][platform]['new_listings'] = threads[platform]['queue'].qsize()

            if threads[platform]['log_queue'].qsize() > 0:
                temp_logs = []
                for _ in range(threads[platform]['log_queue'].qsize()):
                    log = threads[platform]['log_queue'].get()
                    if log['type'] == 'error':
                        response_body['results'][platform]['exception'] = log['exception']

                    temp_logs.append(log)

                for log in temp_logs[::-1]:
                    threads[platform]['log_queue'].put(log)

    return JsonResponse(response_body)


def thread_is_running(name: str) -> bool:
    return any(name == thread.getName() for thread in enum_threads())
