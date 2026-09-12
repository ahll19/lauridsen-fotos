from django.urls import path

from . import views

app_name = "galleries"

urlpatterns = [
    path("<slug:slug>/", views.detail, name="detail"),
    path("<slug:slug>/p/<int:photo_id>/", views.photo, name="photo"),
    path("<slug:slug>/p/<int:photo_id>/download/", views.download_photo, name="download_photo"),
    path("<slug:slug>/download/", views.download_zip, name="download_zip"),
]
