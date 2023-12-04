from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("teste1/", views.teste1, name="teste1"),
    path("teste2/", views.teste2, name="teste2"),
]