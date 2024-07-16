from __future__ import annotations

from itertools import groupby
from json import load, loads
from re import sub

from django.db.models import F
from django.db.models.query_utils import Q
from django.http import HttpRequest, HttpResponse
from django.template import loader
from numpy import arange, split
from unidecode import unidecode

from src.api.models import Listing
from src.extractor.models import ExtractionFilter


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

    full_query = sub(r'/jobs/\?[page=0-9]*', '', request.get_full_path()).replace('/jobs/', '')
    return HttpResponse(
        template.render(
            get_listings(
                search_query, page, listing_query, sorting_query, companies_query, cities_query, platforms_query
            )
            | {'tab_title': 'Vagas', 'full_query': full_query},
            request,
        )
    )


def get_listings(
    search_queries_str: str,
    page: int,
    listing_properties: list[bool],
    sorting_properties: list[str],
    companies: list[str],
    cities: list[str],
    platforms: list[str],
) -> dict:
    filters = {
        key: [value['value'] for value in values]
        for key, values in groupby(
            ExtractionFilter.objects.all().values('category', 'value'), key=lambda x: x['category']
        )
    }
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
        listings_query |= Q(closed=False)
    if listing_properties[7]:
        listings_query |= Q(closed=True)

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
