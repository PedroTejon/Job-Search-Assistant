from __future__ import annotations

from json import loads
from uuid import uuid4

from django.forms.models import model_to_dict
from django.http import HttpRequest, JsonResponse
from django.views.decorators.csrf import csrf_exempt

from src.api.models import Listing
from src.extractor.classes import ExtractionThread
from src.extractor.models import ExtractionFilter, ExtractionLog
from src.extractor.modules import PLATFORM_IDS
from src.extractor.modules.catho import run_pipeline as catho_extraction
from src.extractor.modules.glassdoor import get_listing_details as glassdoor_update
from src.extractor.modules.glassdoor import run_pipeline as glassdoor_extraction
from src.extractor.modules.linkedin import get_listing_details as linkedin_update
from src.extractor.modules.linkedin import run_pipeline as linkedin_extraction
from src.extractor.modules.utils import asciify_text
from src.extractor.modules.vagas_com import run_pipeline as vagas_com_extraction

threads: dict = {}


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
    threading_pipeline = [
        ['catho', catho_extraction],
        ['glassdoor', glassdoor_extraction],
        ['linkedin', linkedin_extraction],
        ['vagas_com', vagas_com_extraction],
    ]

    for platform, function in threading_pipeline:
        if not thread_is_running(function.__name__):
            execution_id = str(uuid4())
            threads[platform] = ExtractionThread(
                target=function,
                name=function.__name__,
                execution_id=execution_id,
            )
            threads[platform].start()

    return JsonResponse({'status': 200})


def get_listing_extraction_status(request: HttpRequest) -> JsonResponse:
    response_body: dict = {
        'status': 200,
        'results': {platform: {} for platform in PLATFORM_IDS},
    }

    for platform, thread in threads.items():
        response_body['results'][platform]['status'] = 'ACTIVE' if thread.is_alive() else 'INACTIVE'
        execution_log = ExtractionLog.objects.get(id=thread.execution_id)
        response_body['results'][platform]['execution_log'] = model_to_dict(execution_log)

    return JsonResponse(response_body)


def thread_is_running(name: str) -> bool:
    return threads[name].is_alive() if name in threads else False


@csrf_exempt
def update_listing_applied_status(request: HttpRequest) -> JsonResponse:
    listing_id = request.GET.get('id')
    listing_updated_value = loads(request.GET.get('value'))
    if listing_id:
        listing = Listing.objects.get(id__iexact=listing_id)
        listing.applied_to = listing_updated_value
        listing.save()
        return JsonResponse({'status': 200})

    return JsonResponse({'status': 404})


@csrf_exempt
def update_extraction_filters(request: HttpRequest) -> JsonResponse:
    filter_value = asciify_text(request.GET.get('filter_value', '').lower())
    filter_type = request.GET.get('filter_type')

    extraction_filter, created = ExtractionFilter.objects.get_or_create(category=filter_type, value=filter_value)

    json_body: dict[str, str | int] = {'status': 200}

    if request.method == 'POST':
        if not created and extraction_filter.value == filter_value:
            return JsonResponse({'status': 409}, status=409)

        extraction_filter.filter_value = filter_value
        extraction_filter.save()
        json_body['added_filter'] = extraction_filter.value
    elif request.method == 'DELETE':
        extraction_filter.delete()

    return JsonResponse(json_body)
