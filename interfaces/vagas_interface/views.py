from django.db.models.query import Q
from django.http import HttpResponse
from django.template import loader
from numpy import arange, split

from interfaces.vagas_interface.models import Company, Listing


def index(request):
    template = loader.get_template('index.html')
    page = int(request.GET.get('page', 1))
    queries_str = request.GET.get('query', '')
    queries = queries_str.split()
    try:
        if not queries:
            pages = split(Listing.objects.values(), arange(50, Listing.objects.count(), 50))
            listings = list(list(pages)[page - 1])
        else:
            query = Q()
            for term in queries:
                query &= Q(title__contains=term)
            pages = split(Listing.objects.filter(query).values(), arange(50, Listing.objects.filter(query).count(), 50))
            listings = list(list(pages)[page - 1])

        for listing in listings:
            company = Company.objects.get(id__exact=listing['company_id'])
            if listing['platform'] == 'LinkedIn':
                listing['company_name'] = company.platforms['linkedin']['name']
            elif listing['platform'] == 'Glassdoor':
                listing['company_name'] = company.platforms['glassdoor']['name']
            elif listing['platform'] == 'Catho':
                listing['company_name'] = company.platforms['catho']['name']
            elif listing['platform'] == 'Vagas.com':
                listing['company_name'] = company.platforms['vagas_com']['name']

        paginations = list(range(max(1, page - 4), min(page + 4, len(pages) + 1)))
        return HttpResponse(template.render({'listings': listings, 'page': page, 'pages': paginations, 'total_pages': len(paginations) - 1, 'query': queries_str}, request))
    except IndexError:
        return HttpResponse(template.render({'listings': [], 'page': page, 'pages': [page], 'total_pages': 0, 'query': queries_str}, request))
