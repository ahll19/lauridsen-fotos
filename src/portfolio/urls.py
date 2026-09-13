from django.urls import path

from . import views

app_name = "portfolio"

urlpatterns = [
    path("portfolio/", views.index, name="index"),
    path("portfolio/<slug:slug>/", views.category, name="category"),
    path("portfolio/<slug:category_slug>/<slug:slug>/", views.album, name="album"),
]
