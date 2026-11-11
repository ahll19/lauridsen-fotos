from django.urls import path
from django.utils.translation import gettext_lazy as _

from . import views

app_name = "pages"

# The paths are translated, so the English site reads /en/pricing/ rather than
# /en/priser/. The Danish forms live in the message catalogue like any other string.
urlpatterns = [
    path("", views.home, name="home"),
    path(_("pricing/"), views.pricing, name="pricing"),
    path(_("contact/"), views.contact, name="contact"),
    path(_("about/"), views.about, name="about"),
]
