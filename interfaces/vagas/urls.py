from django.urls import path

from . import views

urlpatterns = [
    path('', views.index, name='index'),
    path('apply_new_filter', views.apply_new_filter, name='apply_new_filter'),
    path('remove_filter', views.remove_filter, name='remove_filter'),
    path('update_listing_applied_status', views.update_listing_applied_status, name='update_listing_applied_status'),
    path('start_listing_extraction', views.start_listing_extraction, name='start_listing_extraction'),
    path('get_listing_extraction_status', views.get_listing_extraction_status, name='get_listing_extraction_status'),
]
