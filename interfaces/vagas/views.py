from json import dump, load
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
    queries_str = request.GET.get('query', '')
    page = int(request.GET.get('page', 1))
    get_new = request.GET.get('new', True)
    if isinstance(get_new, str):
        get_new = get_new == 'true'
    get_applied_to = request.GET.get('applied', False)
    if isinstance(get_applied_to, str):
        get_applied_to = get_applied_to == 'true'
    get_dismissed = request.GET.get('dismissed', False)
    if isinstance(get_dismissed, str):
        get_dismissed = get_dismissed == 'true'

    return HttpResponse(template.render(get_listings(queries_str, page, [get_applied_to, get_dismissed, get_new]) | {'tab_title': 'Vagas'}, request))


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


def get_listings(queries_str, page, tabs) -> dict:
    queries = unidecode(queries_str).lower().split()
    query = Q()

    # [0] = Applied, [1] = Dismissed, [2] = Not Avaliated
    if tabs[0]:
        query |= Q(applied_to__exact=True)
    if tabs[1]:
        query |= Q(applied_to__exact=False)
    if tabs[2]:
        query |= Q(applied_to__exact=None)

    if not any(tabs):
        query |= Q(applied_to__exact=None)

    try:
        if not queries:
            pages = split(Listing.objects.filter(query).order_by('-id').values(),
                          arange(50, Listing.objects.filter(query).count(), 50))
            listings = list(list(pages)[page - 1])
        else:
            filtered_listings = [listing for listing in Listing.objects.filter(query).order_by('-id').values() for term in queries if term in unidecode(listing['title']).lower()]
            pages = split(filtered_listings, arange(50, len(filtered_listings), 50))
            listings = list(list(pages)[page - 1])

        paginations = range(max(1, page - 4), min(page + 5, len(pages) + 1))
        return {'listings': listings, 'page': page, 'pages': paginations, 'total_pages': len(pages), 'query': queries_str, 'get_applied': tabs[0], 'get_dismissed': tabs[1], 'get_new': tabs[2]}
    except IndexError:
        return {'listings': [], 'page': page, 'pages': [page], 'total_pages': 0, 'query': queries_str, 'get_applied': tabs[0], 'get_dismissed': tabs[1], 'get_new': tabs[2]}


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
