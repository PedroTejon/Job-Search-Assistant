from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    # path("json", views.listings_json, name="listings_json"),
    path("applied_to_listing", views.applied_to_listing, name="applied_to_listing"),
    path("dismiss_listing", views.dismiss_listing, name="dismiss_listing"),
    path("nullify_listing", views.nullify_listing, name="nullify_listing")
]
