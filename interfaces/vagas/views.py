from django.db.models.query import Q
from django.http import HttpResponse, JsonResponse
from django.template import loader
from django.views.decorators.csrf import csrf_exempt
from numpy import arange, split

from interfaces.vagas.models import Listing


def index(request):
    template = loader.get_template('index.html')
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

    return HttpResponse(template.render(get_listings(queries_str, page, [get_applied_to, get_dismissed, get_new]), request))


# def listings_json(request):
#     queries_str = request.GET.get('query', '')
#     page = int(request.GET.get('page', 1))
#     get_new = request.GET.get('new', True)
#     if isinstance(get_new, str):
#         get_new = get_new == 'true'
#     get_applied_to = request.GET.get('applied_to', False)
#     if isinstance(get_applied_to, str):
#         get_applied_to = get_applied_to == 'true'
#     get_dismissed = request.GET.get('dismissed', False)
#     if isinstance(get_dismissed, str):
#         get_dismissed = get_dismissed == 'true'

#     return JsonResponse(get_listings(queries_str, page, [get_applied_to, get_dismissed, get_new]))


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
    try:
        if not queries:
            pages = split(Listing.objects.filter(query).values(), arange(
                50, Listing.objects.filter(query).count(), 50))
            listings = list(list(pages)[page - 1])
        else:
            for term in queries:
                query &= Q(title__contains=term)
            pages = split(Listing.objects.filter(query).values(), arange(50, Listing.objects.filter(query).count(), 50))
            listings = list(list(pages)[page - 1])

        paginations = list(range(max(1, page - 4), min(page + 4, len(pages) + 1)))
        return {'listings': listings, 'page': page, 'pages': paginations, 'total_pages': len(pages), 'query': queries_str, 'get_applied': tabs[0], 'get_dismissed': tabs[1], 'get_new': tabs[2]}
    except IndexError:
        return {'listings': [], 'page': page, 'pages': [page], 'total_pages': 0, 'query': queries_str, 'get_applied': tabs[0], 'get_dismissed': tabs[1], 'get_new': tabs[2]}
