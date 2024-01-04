from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    # path("json", views.listings_json, name="listings_json"),
    path("applied_to_listing", views.applied_to_listing, name="applied_to_listing"),
    path("dismiss_listing", views.dismiss_listing, name="dismiss_listing"),
    path("nullify_listing", views.nullify_listing, name="nullify_listing"),
    path("start_listing_extraction", views.start_listing_extraction, name="start_listing_extraction"),
    path("get_listing_extraction_status", views.get_listing_extraction_status, name="get_listing_extraction_status"),
]
