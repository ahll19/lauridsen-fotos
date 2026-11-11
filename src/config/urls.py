"""
URL routing.

Public pages are wrapped in i18n_patterns so each has a /da/ and /en/ form. Client
galleries and the admin sit outside that — a gallery link handed to a client should not
change shape depending on language, and the admin path is a secret that shouldn't be
duplicated per language.
"""

from django.conf import settings
from django.conf.urls.i18n import i18n_patterns
from django.contrib import admin
from django.contrib.sitemaps.views import sitemap
from django.templatetags.static import static
from django.urls import include, path
from django.utils.translation import gettext_lazy as _
from django.views.generic import RedirectView

from core.sitemaps import SITEMAPS
from core.views import healthz, robots_txt

# The admin is the one interface the owner uses every week; it should say whose it is
# rather than "Django administration".
admin.site.site_header = "Lauridsen Fotos"
admin.site.site_title = "Lauridsen Fotos"
admin.site.index_title = _("Site administration")


class FaviconView(RedirectView):
    """
    Browsers and crawlers ask for /favicon.ico whatever the page's <link> says.

    Redirected to the real file rather than served from here, so the icon stays a static
    asset with a hashed name and a long cache lifetime like every other.
    """

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return static("favicon.svg")


urlpatterns = [
    path(settings.ADMIN_PATH, admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("healthz", healthz, name="healthz"),
    path("robots.txt", robots_txt, name="robots"),
    path("favicon.ico", FaviconView.as_view(), name="favicon"),
    path("sitemap.xml", sitemap, {"sitemaps": SITEMAPS}, name="sitemap"),
    # Unlisted by design: never referenced from navigation, sitemap, or robots.txt.
    path("g/", include("galleries.urls")),
]

urlpatterns += i18n_patterns(
    path("", include("pages.urls")),
    path("", include("portfolio.urls")),
    path("", include("timeline.urls")),
    prefix_default_language=False,
)
