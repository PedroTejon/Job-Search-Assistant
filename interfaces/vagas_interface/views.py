import threading

from numpy import split, arange
from django.http import HttpResponse, JsonResponse
from django.template import loader


from interfaces.vagas_interface.models import Listing, Company


def index(request):
    template = loader.get_template('index.html')
    listings = Listing.objects.values()[:min(Listing.objects.count(), 50)] if Listing.objects.count() >= 1 else []
    return HttpResponse(template.render({'listings': listings}, request))


def pagination(request, page):
    template = loader.get_template('index.html')
    if page >= 1:
        try:
            listings = list(split(Listing.objects.values(), arange(50, Listing.objects.count(), 50)))[page - 1]
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
            return HttpResponse(template.render({'listings': listings}, request))
        except IndexError:
            return HttpResponse(template.render({'listings': []}, request))

    return HttpResponse(template.render({'listings': []}, request))


def teste1(request):
    if not any(filter(lambda x: x.name == 'scraper', threading.enumerate())):
        pass
    return JsonResponse({'teste': 'Hello, trestee1index.'})


def teste2(request):
    return JsonResponse({'teste': 'teste2222.'})
