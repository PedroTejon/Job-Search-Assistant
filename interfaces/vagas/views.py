from queue import Queue
from threading import Thread
from threading import enumerate as enum_threads

from django.db.models.query import Q
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
from numpy import arange, split

from interfaces.vagas.models import Listing
from modules.catho import get_jobs as catho_extraction
from modules.glassdoor import get_jobs as glassdoor_extraction
from modules.linkedin import get_jobs as linkedin_extraction
from modules.vagas_com import get_jobs as vagas_com_extraction
from modules.utils import reload_filters


threads = {
    'linkedin': {
        'thread': None,
        'queue': None
    },
    'glassdoor': {
        'thread': None,
        'queue': None
    },
    'catho': {
        'thread': None,
        'queue': None
    },
    'vagas_com': {
        'thread': None,
        'queue': None
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


def get_listings(queries_str, page, tabs) -> dict:
    queries = queries_str.split()
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
            pages = split(Listing.objects.filter(query).values(), arange(50, Listing.objects.filter(query).count(), 50))
            listings = list(list(pages)[page - 1])
        else:
            for term in queries:
                query &= Q(title__contains=term)
            pages = split(Listing.objects.filter(query).values(), arange(50, Listing.objects.filter(query).count(), 50))
            listings = list(list(pages)[page - 1])

        paginations = list(range(max(1, page - 4), min(page + 5, len(pages) + 1)))
        return {'listings': listings, 'page': page, 'pages': paginations, 'total_pages': len(pages), 'query': queries_str, 'get_applied': tabs[0], 'get_dismissed': tabs[1], 'get_new': tabs[2]}
    except IndexError:
        return {'listings': [], 'page': page, 'pages': [page], 'total_pages': 0, 'query': queries_str, 'get_applied': tabs[0], 'get_dismissed': tabs[1], 'get_new': tabs[2]}


@csrf_exempt
def start_listing_extraction(request):
    global threads
    if not thread_is_running('linkedin_extraction') and not thread_is_running('glassdoor_extraction') and not thread_is_running('catho_extraction') and not thread_is_running('vagas_com_extraction'):
        reload_filters()
        
        threads['linkedin']['queue'] = Queue()
        threads['linkedin']['thread'] = Thread(target=linkedin_extraction, name='linkedin_extraction', args=[
                                               threads['linkedin']['queue']])
        threads['linkedin']['thread'].start()

        threads['glassdoor']['queue'] = Queue()
        threads['glassdoor']['thread'] = Thread(target=glassdoor_extraction, name='glassdoor_extraction', args=[
                                                threads['glassdoor']['queue']])
        threads['glassdoor']['thread'].start()

        threads['catho']['queue'] = Queue()
        threads['catho']['thread'] = Thread(target=catho_extraction, name='catho_extraction', args=[
                                            threads['catho']['queue']])
        threads['catho']['thread'].start()

        threads['vagas_com']['queue'] = Queue()
        threads['vagas_com']['thread'] = Thread(target=vagas_com_extraction, name='vagas_com_extraction', args=[
                                                threads['vagas_com']['queue']])
        threads['vagas_com']['thread'].start()

    return JsonResponse({'status': 200})


def get_listing_extraction_status(request):
    return JsonResponse({
        'status': 200,
        'results': {
            'linkedin': {
                'status': threads['linkedin']['thread'].is_alive() if threads['linkedin']['thread'] is not None else False,
                'new_listings': threads['linkedin']['queue'].qsize()
            },
            'glassdoor': {
                'status': threads['glassdoor']['thread'].is_alive() if threads['glassdoor']['thread'] is not None else False,
                'new_listings': threads['glassdoor']['queue'].qsize()
            },
            'catho': {
                'status': threads['catho']['thread'].is_alive() if threads['catho']['thread'] is not None else False,
                'new_listings': threads['catho']['queue'].qsize()
            },
            'vagas_com': {
                'status': threads['vagas_com']['thread'].is_alive() if threads['vagas_com']['thread'] is not None else False,
                'new_listings': threads['vagas_com']['queue'].qsize()
            }
        }
    })


def thread_is_running(name):
    return any(map(lambda thr: name == thr.getName(), enum_threads()))
