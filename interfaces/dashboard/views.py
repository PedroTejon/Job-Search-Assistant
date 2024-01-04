from django.http import HttpResponse
from django.template import loader


def index(request):
    template = loader.get_template('dashboard.html')

    return HttpResponse(template.render({'tab_title': 'Dashboard'}, request))
