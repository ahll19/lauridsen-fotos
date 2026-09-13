"""
Tests for the things that sit between the application and the outside world.

Most of these exist because the corresponding bug shipped: a template comment that
rendered on every page, a rate limit that turned out to be global, an address recorded
from a header the caller controls.
"""

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from core.middleware import real_client_ip
from portfolio.models import Album, Category
from timeline.models import TimelineEntry


class RenderedPageTests(TestCase):
    """
    A crawl of the public pages, asserting they contain no unrendered template syntax.

    `{# … #}` is a single-line construct: spread over two lines it is not a comment at
    all, and Django emits it into the page. One such comment in base.html put a note to
    the developer into the navigation of all thirty-four pages, and the whole pipeline
    passed, because nothing had ever looked at a rendered page.
    """

    PATHS = [
        "/",
        "/en/",
        "/portfolio/",
        "/en/portfolio/",
        "/timeline/",
        "/en/timeline/",
        "/priser/",
        "/en/priser/",
        "/kontakt/",
        "/en/kontakt/",
        "/om/",
        "/en/om/",
    ]

    def test_no_unrendered_template_syntax(self):
        for path in self.PATHS:
            with self.subTest(path=path):
                body = self.client.get(path).content.decode()
                for token in ("{#", "{%", "{{"):
                    self.assertNotIn(token, body, f"{token} leaked into {path}")

    def test_every_public_page_answers(self):
        for path in self.PATHS:
            with self.subTest(path=path):
                self.assertEqual(self.client.get(path).status_code, 200)


@override_settings(TRUSTED_PROXY_COUNT=1)
class ClientIPTests(TestCase):
    """
    The address must come from the trusted end of X-Forwarded-For.

    nginx appends the address it actually saw, so the right-hand entry is ours and
    everything left of it is whatever the caller chose to send.
    """

    def _request(self, **meta):
        request = type("R", (), {})()
        request.META = meta
        return request

    def test_uses_the_rightmost_entry(self):
        ip = real_client_ip(
            self._request(
                REMOTE_ADDR="172.18.0.4",
                HTTP_X_FORWARDED_FOR="203.0.113.99, 198.51.100.7",
            )
        )
        self.assertEqual(ip, "198.51.100.7")

    def test_ignores_a_forged_left_hand_entry(self):
        """A caller inventing a chain cannot make themselves look like another address."""
        ip = real_client_ip(
            self._request(
                REMOTE_ADDR="172.18.0.4",
                HTTP_X_FORWARDED_FOR="1.2.3.4, 5.6.7.8, 198.51.100.7",
            )
        )
        self.assertEqual(ip, "198.51.100.7")

    def test_falls_back_to_remote_addr_without_the_header(self):
        self.assertEqual(real_client_ip(self._request(REMOTE_ADDR="192.0.2.1")), "192.0.2.1")

    def test_short_chain_does_not_hand_back_a_supplied_value(self):
        """With a chain shorter than the trusted hop count, never walk past its start."""
        with override_settings(TRUSTED_PROXY_COUNT=3):
            ip = real_client_ip(
                self._request(REMOTE_ADDR="172.18.0.4", HTTP_X_FORWARDED_FOR="203.0.113.99")
            )
        self.assertEqual(ip, "203.0.113.99")

    def test_middleware_replaces_remote_addr(self):
        """End to end: what a view sees is the real address, not the proxy's."""
        client = Client(REMOTE_ADDR="172.18.0.4")
        response = client.post(
            reverse("pages:contact"),
            {"name": "Test", "email": "t@example.com", "message": "Hello"},
            HTTP_X_FORWARDED_FOR="203.0.113.99, 198.51.100.7",
        )
        self.assertEqual(response.status_code, 200)
        from pages.models import ContactSubmission

        self.assertEqual(ContactSubmission.objects.get().ip_address, "198.51.100.7")


class SitemapTests(TestCase):
    def setUp(self):
        self.published = Category.objects.create(name="Weddings", slug="weddings", visible=True)
        self.draft = Category.objects.create(name="Drafts", slug="drafts", visible=False)
        Album.objects.create(category=self.published, name="A", slug="a", visible=True)
        self.hidden_album = Album.objects.create(
            category=self.draft, name="Unannounced", slug="unannounced", visible=True
        )
        TimelineEntry.objects.create(title="Entry", slug="entry", date="2026-01-01", visible=True)

    def test_album_in_an_unpublished_category_is_absent(self):
        """
        Its category is not published, so its page 404s and its name is not public yet.

        Listing it advertised both the URL and the name of work still being prepared.
        """
        body = self.client.get("/sitemap.xml").content.decode()
        self.assertNotIn("unannounced", body)

    def test_both_languages_are_listed(self):
        body = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("/portfolio/weddings/", body)
        self.assertIn("/en/portfolio/weddings/", body)
        self.assertIn("hreflang", body)

    @override_settings(ALLOWED_HOSTS=["lauridsen-fotos.dk"])
    def test_urls_use_the_requesting_host(self):
        """Not django.contrib.sites, whose unconfigured default is example.com."""
        body = self.client.get("/sitemap.xml", HTTP_HOST="lauridsen-fotos.dk").content.decode()
        self.assertIn("lauridsen-fotos.dk", body)
        self.assertNotIn("example.com", body)

    def test_no_gallery_url_appears(self):
        body = self.client.get("/sitemap.xml").content.decode()
        self.assertNotIn("/g/", body)
