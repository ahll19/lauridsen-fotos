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
from django.urls import include, path

from core.sitemaps import SITEMAPS
from core.views import design_choose, design_index, healthz, robots_txt

urlpatterns = [
    path(settings.ADMIN_PATH, admin.site.urls),
    path("i18n/", include("django.conf.urls.i18n")),
    path("healthz", healthz, name="healthz"),
    path("robots.txt", robots_txt, name="robots"),
    # Temporary, while a visual direction is chosen (ROADMAP 0.2.0). The views 404 unless
    # DESIGN_PREVIEW_ENABLED, so these routes are inert in production.
    path("design/", design_index, name="design_index"),
    path("design/choose/", design_choose, name="design_choose"),
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
