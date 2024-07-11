from __future__ import annotations

from json import dump, load, loads
from queue import Queue
from threading import Thread
from threading import enumerate as enum_threads
from typing import TypedDict

from django.forms.models import model_to_dict
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from src.api.models import Listing
from src.extractor.modules import PLATFORM_IDS
from src.extractor.modules.catho import get_jobs as catho_extraction
from src.extractor.modules.glassdoor import get_jobs as glassdoor_extraction
from src.extractor.modules.glassdoor import get_listing_details as glassdoor_update
from src.extractor.modules.linkedin import get_jobs as linkedin_extraction
from src.extractor.modules.linkedin import get_listing_details as linkedin_update
from src.extractor.modules.utils import asciify_text, reload_filters
from src.extractor.modules.vagas_com import get_jobs as vagas_com_extraction

threads: dict = {
    platform: {'thread': Thread(), 'queue': Queue(), 'log_queue': Queue()} for platform in PLATFORM_IDS
}


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


@csrf_exempt
def start_listing_extraction(request: HttpRequest) -> JsonResponse:
    if not any(thread_is_running(platform + '_extraction') for platform in PLATFORM_IDS):
        reload_filters()

        for platform in PLATFORM_IDS:
            thread_func = globals()[platform + '_extraction']
            threads[platform]['queue'] = Queue()
            threads[platform]['log_queue'] = Queue()
            threads[platform]['thread'] = Thread(
                target=thread_func,
                name=platform + '_extraction',
                args=[threads[platform]['queue'], threads[platform]['log_queue']],
            )
            threads[platform]['thread'].start()
        return JsonResponse({'status': 200})

    return JsonResponse({'status': 409}, status=409)


def get_listing_extraction_status(request: HttpRequest) -> JsonResponse:  # noqa: ARG001
    response_body: dict = {
        'status': 200,
        'results': {platform: {'status': False, 'new_listings': 0} for platform in PLATFORM_IDS},
    }

    for platform, value in threads.items():
        if value['queue'] is not None:
            response_body['results'][platform]['status'] = (
                value['thread'].is_alive() if value['thread'] is not None else False
            )
            response_body['results'][platform]['new_listings'] = value['queue'].qsize()

            if value['log_queue'].qsize() > 0:
                temp_logs = []
                for _ in range(value['log_queue'].qsize()):
                    log = value['log_queue'].get()
                    if log['type'] == 'error':
                        response_body['results'][platform]['exception'] = log['exception']

                    temp_logs.append(log)

                for log in temp_logs[::-1]:
                    value['log_queue'].put(log)

    return JsonResponse(response_body)


def thread_is_running(name: str) -> bool:
    return any(name == thread.getName() for thread in enum_threads())


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

    with open('src/data/filters.json', encoding='utf-8') as filters_f:
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

    with open('src/data/filters.json', 'w', encoding='utf-8') as filters_f:
        dump(filters, filters_f, ensure_ascii=False)

    for platform in PLATFORM_IDS:
        if threads[platform]['thread'] is not None and threads[platform]['thread'].is_alive():
            threads[platform]['log_queue'].put({'type': 'reload_request'})

    return JsonResponse(json_body)
