from django.contrib import admin
from django.urls import include, path
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(url='jobs/', permanent=False)),
    path('jobs/', include('src.api.urls')),
    path('extractor/', include('src.extractor.urls')),
    path('admin/', admin.site.urls),
]
