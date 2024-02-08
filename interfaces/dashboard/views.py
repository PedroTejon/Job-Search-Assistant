from django.http import HttpRequest, HttpResponse
from django.template import loader


def index(request: HttpRequest) -> HttpResponse:
    template = loader.get_template('dashboard.html')

    return HttpResponse(template.render({'tab_title': 'Dashboard'}, request))
