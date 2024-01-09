from json import dump, load, loads
from queue import Queue
from threading import Thread
from threading import enumerate as enum_threads

from django.db.models.query import Q
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
from numpy import arange, split
from unidecode import unidecode

from interfaces.vagas.models import Listing
from modules.catho import get_jobs as catho_extraction
from modules.glassdoor import get_jobs as glassdoor_extraction
from modules.linkedin import get_jobs as linkedin_extraction
from modules.utils import asciify_text, reload_filters
from modules.vagas_com import get_jobs as vagas_com_extraction

threads = {
    'linkedin': {
        'thread': None,
        'queue': None,
        'log_queue': None
    },
    'glassdoor': {
        'thread': None,
        'queue': None,
        'log_queue': None
    },
    'catho': {
        'thread': None,
        'queue': None,
        'log_queue': None
    },
    'vagas_com': {
        'thread': None,
        'queue': None,
        'log_queue': None
    }
}


def index(request):
    template = loader.get_template('vagas.html')
    page = int(request.GET.get('page', 1))
    search_query = request.GET.get('query', '')
    listing_query = request.GET.get('listing', [False, False, True, True, True])
    if isinstance(listing_query, str):
        listing_query = loads(listing_query)
    companies_query = request.GET.get('companies', [])
    if isinstance(companies_query, str):
        companies_query = loads(companies_query)
    cities_query = request.GET.get('cities', [])
    if isinstance(cities_query, str):
        cities_query = loads(cities_query)

    return HttpResponse(template.render(get_listings(search_query, page, listing_query, companies_query, cities_query) | {'tab_title': 'Vagas'}, request))


@csrf_exempt
def applied_to_listing(request):
    listing_id = request.GET.get('id')
    if listing_id:
        listing = Listing.objects.get(id__iexact=listing_id)
        listing.applied_to = True
        listing.save()
        return JsonResponse({'status': 200})

    return JsonResponse({'status': 404})


@csrf_exempt
def dismiss_listing(request):
    listing_id = request.GET.get('id')
    if listing_id:
        listing = Listing.objects.get(id__iexact=listing_id)
        listing.applied_to = False
        listing.save()
        return JsonResponse({'status': 200})

    return JsonResponse({'status': 404})


@csrf_exempt
def nullify_listing(request):
    listing_id = request.GET.get('id')
    if listing_id:
        listing = Listing.objects.get(id__iexact=listing_id)
        listing.applied_to = None
        listing.save()
        return JsonResponse({'status': 200})

    return JsonResponse({'status': 404})


@csrf_exempt
def apply_new_filter(request):
    filtered = request.GET.get('filtered').lower()
    filter_type = request.GET.get('filter_type', 'title_exclude_words')

    with open('data/filters.json', 'r', encoding='utf-8') as f:
        filters = load(f)

    if filtered not in filters[filter_type]:
        filters[filter_type].append(asciify_text(filtered))

    for platform in ['linkedin', 'glassdoor', 'catho', 'vagas_com']:
        if threads[platform]['thread'] is not None and threads[platform]['thread'].is_alive():
            threads[platform]['log_queue'].put({'type': 'reload_request'})

    listings = Listing.objects.all().filter(applied_to__exact=None)
    for listing in listings:
        title = asciify_text(listing.title)
        company_name = asciify_text(listing.company_name)
        if (any(word in title.split() for word in filters['title_exclude_words']) or any(term in title for term in filters['title_exclude_terms']) or any(word in company_name.split() for word in filters['company_exclude_words']) or any(term in company_name for term in filters['company_exclude_terms'])) and (listing.applied_to is None or listing.applied_to):
            listing.applied_to = False
            listing.save()

    with open('data/filters.json', 'w', encoding='utf-8') as f:
        dump(filters, f, ensure_ascii=False)

    return JsonResponse({'status': 200})


def get_listings(queries_str, page, listing_properties, companies, cities) -> dict:
    queries = unidecode(queries_str).lower().split()
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

    query = listings_query & workplace_type_query

    try:
        if not queries:
            queried_listings = Listing.objects.filter(query).order_by('-id').values()
        else:
            queried_listings = [listing for listing in Listing.objects.filter(query).order_by('-id').values() for term in queries if term in unidecode(listing['title']).lower()]

        if companies:
            queried_listings = [listing for listing in queried_listings for company in companies if unidecode(company).lower() in unidecode(listing['company_name']).lower()]
        if cities:
            queried_listings = [listing for listing in queried_listings for city in cities if unidecode(city).lower() in unidecode(listing['location']).lower()]

        pages = split(queried_listings, arange(50, len(queried_listings), 50))
        listings = list(list(pages)[page - 1])

        paginations = range(max(1, page - 4), min(page + 5, len(pages) + 1))
        return {'listings': listings, 'page': page, 'pages': paginations, 'total_pages': len(pages), 'query': queries_str, 'listing_properties': listing_properties, 'companies': companies, 'cities': cities, 'listing_count': len(listings)}
    except IndexError:
        return {'listings': [], 'page': page, 'pages': [page], 'total_pages': 0, 'query': queries_str, 'listing_properties': listing_properties, 'companies': companies, 'cities': cities, 'listing_count': 0}


@csrf_exempt
def start_listing_extraction(request):  # pylint: disable=W0613
    global threads
    if not thread_is_running('linkedin_extraction') and not thread_is_running('glassdoor_extraction') and not thread_is_running('catho_extraction') and not thread_is_running('vagas_com_extraction'):
        reload_filters()

        threads['linkedin']['queue'] = Queue()
        threads['linkedin']['log_queue'] = Queue()
        threads['linkedin']['thread'] = Thread(target=linkedin_extraction, name='linkedin_extraction', args=[
                                               threads['linkedin']['queue'],
                                               threads['linkedin']['log_queue']])
        threads['linkedin']['thread'].start()

        threads['glassdoor']['queue'] = Queue()
        threads['glassdoor']['log_queue'] = Queue()
        threads['glassdoor']['thread'] = Thread(target=glassdoor_extraction, name='glassdoor_extraction', args=[
                                                threads['glassdoor']['queue'],
                                                threads['glassdoor']['log_queue']])
        threads['glassdoor']['thread'].start()

        threads['catho']['queue'] = Queue()
        threads['catho']['log_queue'] = Queue()
        threads['catho']['thread'] = Thread(target=catho_extraction, name='catho_extraction', args=[
                                            threads['catho']['queue'],
                                            threads['catho']['log_queue']])
        threads['catho']['thread'].start()

        threads['vagas_com']['queue'] = Queue()
        threads['vagas_com']['log_queue'] = Queue()
        threads['vagas_com']['thread'] = Thread(target=vagas_com_extraction, name='vagas_com_extraction', args=[
                                                threads['vagas_com']['queue'],
                                                threads['vagas_com']['log_queue']])
        threads['vagas_com']['thread'].start()

        return JsonResponse({'status': 200})

    return JsonResponse({'status': 409}, status=409)


def get_listing_extraction_status(request):  # pylint: disable=W0613
    response_body = {
        'status': 200,
        'results': {
            'linkedin': {
                'status': False,
                'new_listings': 0
            },
            'glassdoor': {
                'status': False,
                'new_listings': 0
            },
            'catho': {
                'status': False,
                'new_listings': 0
            },
            'vagas_com': {
                'status': False,
                'new_listings': 0
            }
        }
    }

    for platform in ['linkedin', 'glassdoor', 'catho', 'vagas_com']:
        if threads[platform]['queue'] is not None:
            response_body['results'][platform]['status'] = threads[platform]['thread'].is_alive(
            ) if threads[platform]['thread'] is not None else False
            response_body['results'][platform]['new_listings'] = threads[platform]['queue'].qsize()

            if threads[platform]['log_queue'].qsize() > 0:
                temp_logs = []
                for _ in range(threads[platform]['log_queue'].qsize()):
                    log = threads[platform]['log_queue'].get()
                    if log['type'] == 'error':
                        response_body['results'][platform]['exception'] = f"{log['exception']}: {log['file_name']}, linha {log['file_line']}"

                    temp_logs.append(log)

                for log in temp_logs[::-1]:
                    threads[platform]['log_queue'].put(log)

    return JsonResponse(response_body)


def thread_is_running(name):
    return any(map(lambda thr: name == thr.getName(), enum_threads()))
