from pages.models import ContactSettings, HomeSettings


def site_context(request):
    """Values every template needs: business name for the header, contact details for the footer."""
    home = HomeSettings.get_solo()
    return {
        "site_name": home.business_name,
        "site_tagline": home.tagline,
        # The fallback description for any page that has none of its own.
        "site_description": " ".join((home.intro or home.tagline or "").split())[:160],
        "contact_settings": ContactSettings.get_solo(),
    }
