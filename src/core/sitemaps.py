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
    changefreq = "monthly"
    priority = 0.8

    def items(self):
        return Category.objects.visible()


class AlbumSitemap(Sitemap):
    changefreq = "monthly"
    priority = 0.7

    def items(self):
        return Album.objects.visible().select_related("category")


class TimelineSitemap(Sitemap):
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
