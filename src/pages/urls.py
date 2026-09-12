from django.urls import path

from . import views

app_name = "pages"

urlpatterns = [
    path("", views.home, name="home"),
    path("priser/", views.pricing, name="pricing"),
    path("kontakt/", views.contact, name="contact"),
    path("om/", views.about, name="about"),
]
