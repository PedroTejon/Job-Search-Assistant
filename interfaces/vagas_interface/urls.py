from django.urls import path

from . import views

urlpatterns = [
    path("", views.index, name="index"),
    path("page/<int:page>/", views.pagination, name="pagination"),
    path("teste2/", views.teste2, name="teste2"),
]