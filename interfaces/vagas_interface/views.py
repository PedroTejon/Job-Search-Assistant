from django.http import HttpResponse, JsonResponse
from django.template import loader
from time import sleep
import threading


def index(request):
    template = loader.get_template('index.html')
    return HttpResponse(template.render({}, request))


def teste1(request):
    if not any(filter(lambda x: x.name == 'scraper', threading.enumerate())):
        pass
    return JsonResponse({'teste': 'Hello, trestee1index.'})


def teste2(request):
    return JsonResponse({'teste': 'teste2222.'})
