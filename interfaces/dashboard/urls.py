from django.urls import path

from interfaces.dashboard.views import index

urlpatterns = [
    path("", index, name="index")
]
