from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class PortfolioConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "portfolio"
    # Without this the admin shows the raw app label, in English.
    verbose_name = _("Portfolio")
