from django.conf import settings

from pages.models import ContactSettings, HomeSettings

from . import themes


def site_context(request):
    """Values every template needs: business name for the header, contact details for the footer."""
    home = HomeSettings.get_solo()
    return {
        "site_name": home.business_name,
        "site_tagline": home.tagline,
        "contact_settings": ContactSettings.get_solo(),
    }


def design_preview(request):
    """
    The visual direction currently being previewed (ROADMAP 0.2.0).

    Off unless DESIGN_PREVIEW_ENABLED, in which case every page can be viewed in any of the
    candidate directions and the switcher appears. Temporary by design.
    """
    if not settings.DESIGN_PREVIEW_ENABLED:
        return {"design_preview": False, "theme": themes.DEFAULT}

    return {
        "design_preview": True,
        "theme": themes.get(request.COOKIES.get(settings.THEME_COOKIE_NAME)),
        "themes": themes.THEMES,
    }
