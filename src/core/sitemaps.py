"""
The public sitemap.

Client galleries are structurally absent: this module only knows about models that are
public by definition, so an unlisted gallery cannot leak into the sitemap by accident.
"""

from django.contrib.sitemaps import Sitemap
from django.urls import reverse

from portfolio.models import Album, Category
from timeline.models import TimelineEntry


class StaticViewSitemap(Sitemap):
    # Every public URL exists in Danish and English, so each is listed in both, with
    # reciprocal hreflang alternates. Without this the English half of the site is
    # invisible to search engines.
    i18n = True
    alternates = True
    changefreq = "monthly"
    priority = 0.6

    def items(self):
        return [
            "pages:home",
            "pages:pricing",
            "pages:contact",
            "pages:about",
            "portfolio:index",
            "timeline:index",
        ]

    def location(self, item):
        return reverse(item)


class CategorySitemap(Sitemap):
    i18n = True
    alternates = True
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Category.objects.published()


class AlbumSitemap(Sitemap):
    i18n = True
    alternates = True
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        # An album is only reachable if its category is published too — the album view
        # requires both. Listing a visible album inside a hidden category advertised a URL
        # that answers 404, and published the name and slug of work the owner was still
        # preparing, which is the thing "hidden" exists to prevent.
        return Album.objects.visible().filter(category__visible=True).select_related("category")


class TimelineSitemap(Sitemap):
    i18n = True
    alternates = True
    changefreq = "weekly"
    priority = 0.5

    def items(self):
        return TimelineEntry.objects.visible()

    def lastmod(self, obj):
        return obj.date


SITEMAPS = {
    "static": StaticViewSitemap,
    "categories": CategorySitemap,
    "albums": AlbumSitemap,
    "timeline": TimelineSitemap,
}
