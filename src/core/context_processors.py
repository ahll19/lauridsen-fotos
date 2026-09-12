from pages.models import ContactSettings, HomeSettings


def site_context(request):
    """Values every template needs: business name for the header, contact details for the footer."""
    home = HomeSettings.get_solo()
    return {
        "site_name": home.business_name,
        "site_tagline": home.tagline,
        "contact_settings": ContactSettings.get_solo(),
    }
