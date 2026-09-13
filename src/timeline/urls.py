from django.urls import path

from . import views

app_name = "timeline"

urlpatterns = [
    path("timeline/", views.index, name="index"),
    path("timeline/<slug:slug>/", views.entry, name="entry"),
]
