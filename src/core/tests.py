"""
Tests for the things that sit between the application and the outside world.

Most of these exist because the corresponding bug shipped: a template comment that
rendered on every page, a rate limit that turned out to be global, an address recorded
from a header the caller controls.
"""

import re
from io import StringIO
from pathlib import Path

from django.conf import settings
from django.template.loader import get_template
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
        "/en/pricing/",
        "/kontakt/",
        "/en/contact/",
        "/om/",
        "/en/about/",
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


class ErrorPageTests(TestCase):
    """
    The pages nobody looks at until the day they matter.

    With DJANGO_DEBUG=0 Django stops producing tracebacks and renders these templates
    instead. Before they existed the site answered a mistyped address with an unstyled
    English paragraph, on a site that is otherwise Danish by default.
    """

    def test_404_is_the_sites_own_page(self):
        response = self.client.get("/ingen-saadan-side/")
        self.assertEqual(response.status_code, 404)
        body = response.content.decode()
        self.assertIn("site-header", body, "not the site's own 404 — Django's fallback")
        self.assertIn("404", body)

    def test_404_takes_the_language_from_the_url(self):
        """Danish by default and English under /en/, like every other page."""
        self.assertContains(
            self.client.get("/ingen-saadan-side/"), '<html lang="da"', status_code=404
        )
        self.assertContains(
            self.client.get("/en/no-such-page/"), '<html lang="en"', status_code=404
        )

    def test_404_does_not_invite_indexing(self):
        self.assertContains(self.client.get("/ingen-saadan-side/"), "noindex", status_code=404)

    def test_csrf_failure_renders_the_sites_own_403(self):
        """
        The only 403 this site actually produces, and it very nearly went unstyled.

        Django does not route CSRF failures through handler403 — it calls
        CSRF_FAILURE_VIEW, whose default renders a separate 403_csrf.html with no request
        and no context processors. So adding 403.html was not enough: the page a visitor
        met was still Django's bare built-in one.
        """
        client = Client(enforce_csrf_checks=True)
        response = client.post(reverse("pages:contact"), {"name": "Test"})

        self.assertEqual(response.status_code, 403)
        body = response.content.decode()
        self.assertIn("site-header", body, "still Django's built-in CSRF page")
        self.assertIn("403", body)

    def test_csrf_failure_is_in_the_language_of_the_page(self):
        client = Client(enforce_csrf_checks=True)
        self.assertContains(
            client.post("/en/contact/", {"name": "Test"}), '<html lang="en"', status_code=403
        )

    def test_500_renders_with_no_context_at_all(self):
        """
        django.views.defaults.server_error calls render() with no arguments: no request,
        no context processors, nothing. A 500 page that needs any of those raises a second
        exception inside the handler for the first, and the visitor gets Django's bare
        "A server error occurred" — at the exact moment the site is already failing.
        """
        html = get_template("500.html").render()
        self.assertIn("500", html)

    def test_500_depends_on_nothing_that_could_be_what_broke(self):
        """
        The guard behind the test above, stated where someone editing the file will see it.

        {% extends %} would pull in base.html's site settings lookup, and {% static %}
        would pull in the staticfiles manifest. Either is a plausible cause of the very
        error being reported, so neither may appear on the page reporting it.
        """
        source = (Path(settings.BASE_DIR) / "templates" / "500.html").read_text()
        # The template's own comment block explains why these tags are absent, so it names
        # every one of them. Scan the markup that actually renders, not the prose about it.
        markup = re.sub(r"\{% comment %\}.*?\{% endcomment %\}", "", source, flags=re.S)
        for tag in ("{% extends", "{% static", "{% include"):
            self.assertNotIn(tag, markup, f"500.html must not depend on {tag}")


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


class TranslatedUrlTests(TestCase):
    """English pages have English addresses, and each language's address is its own."""

    PAIRS = [("/priser/", "/en/pricing/"), ("/kontakt/", "/en/contact/"), ("/om/", "/en/about/")]

    def test_each_language_answers_on_its_own_slug(self):
        for danish, english in self.PAIRS:
            with self.subTest(danish=danish):
                self.assertEqual(self.client.get(danish).status_code, 200)
                self.assertEqual(self.client.get(english).status_code, 200)

    def test_a_danish_slug_under_the_english_prefix_does_not_exist(self):
        # Otherwise every page has two English addresses and search engines pick one.
        self.assertEqual(self.client.get("/en/priser/").status_code, 404)

    def test_the_language_switcher_links_to_the_translated_address(self):
        body = self.client.get("/priser/").content.decode()
        self.assertIn('name="next" value="/en/pricing/"', body)
        body = self.client.get("/en/pricing/").content.decode()
        self.assertIn('name="next" value="/priser/"', body)

    def test_the_sitemap_lists_the_translated_address(self):
        body = self.client.get("/sitemap.xml").content.decode()
        self.assertIn("/en/pricing/", body)
        self.assertNotIn("/en/priser/", body)


class PageMetadataTests(TestCase):
    """What a pasted link shows: a title, a description, and no private page among them."""

    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(
            name="Bryllupper",
            slug="bryllupper",
            description="To mennesker og en lang dag.",
            visible=True,
        )
        cls.album = Album.objects.create(
            category=category, name="Sofie & Jonas", slug="sofie-jonas", visible=True
        )

    def test_public_page_describes_itself(self):
        body = self.client.get(self.album.get_absolute_url()).content.decode()
        self.assertIn('<meta property="og:title" content="Sofie &amp; Jonas">', body)
        # The album has no description of its own, so its category's stands in.
        self.assertIn('<meta name="description" content="To mennesker og en lang dag.">', body)
        self.assertIn('property="og:url" content="http://testserver/portfolio/', body)

    def test_error_page_carries_no_preview_tags(self):
        body = self.client.get("/no-such-page/").content.decode()
        self.assertNotIn("og:title", body)

    def test_body_has_no_empty_class_attribute(self):
        self.assertNotIn('class=""', self.client.get("/kontakt/").content.decode())

    def test_fonts_are_not_loaded_from_a_third_party(self):
        body = self.client.get("/").content.decode()
        self.assertNotIn("fonts.googleapis.com", body)
        self.assertNotIn("fonts.gstatic.com", body)

    def test_favicon_is_linked_and_answers(self):
        self.assertIn('rel="icon"', self.client.get("/").content.decode())
        response = self.client.get("/favicon.ico")
        self.assertEqual(response.status_code, 302)
        self.assertIn("favicon", response["Location"])


class ContentSecurityPolicyTests(TestCase):
    def test_pages_carry_a_policy_naming_no_other_host(self):
        policy = self.client.get("/")["Content-Security-Policy"]
        self.assertIn("default-src 'self'", policy)
        self.assertIn("script-src 'self'", policy)
        self.assertNotIn("http", policy)

    def test_no_page_template_carries_an_inline_script(self):
        # script-src 'self' silently disables one, so it would simply stop working.
        for template in (Path(settings.BASE_DIR) / "templates").rglob("*.html"):
            with self.subTest(template=template.name):
                self.assertIsNone(re.search(r"<script(?![^>]*\bsrc=)", template.read_text()))

    @override_settings(
        CONTENT_SECURITY_POLICY="default-src 'none'", CONTENT_SECURITY_POLICY_REPORT_ONLY=True
    )
    def test_report_only_sends_the_other_header(self):
        response = self.client.get("/")
        self.assertNotIn("Content-Security-Policy", response)
        self.assertEqual(response["Content-Security-Policy-Report-Only"], "default-src 'none'")

    @override_settings(CONTENT_SECURITY_POLICY="")
    def test_an_empty_policy_sends_nothing(self):
        self.assertNotIn("Content-Security-Policy", self.client.get("/"))


@override_settings(SECURE_SSL_REDIRECT=True, SECURE_REDIRECT_EXEMPT=[r"^healthz$"])
class HealthCheckOverHttpTests(TestCase):
    """
    The container health check reaches gunicorn over plain HTTP.

    Found by the first rehearsal deploy: with HTTPS enforced the probe was redirected to
    a port that speaks no TLS, the container never became healthy, and the reverse proxy
    waiting on it never started. Nothing local could show it, because running production
    mode on a laptop means turning HTTPS off.
    """

    def test_health_check_is_not_redirected(self):
        self.assertEqual(self.client.get("/healthz").status_code, 200)

    def test_everything_else_still_is(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 301)
        self.assertTrue(response["Location"].startswith("https://"))

    def test_the_exemption_is_what_production_settings_carry(self):
        # The override above mirrors settings.py; this pins the two together.
        source = (Path(settings.BASE_DIR) / "config" / "settings.py").read_text()
        self.assertIn('SECURE_REDIRECT_EXEMPT = [r"^healthz$"]', source)


class ErrorReportTests(TestCase):
    def test_deliberate_error_is_mailed_to_the_owner(self):
        from django.core import mail
        from django.core.management import call_command

        call_command("test_error_report", stdout=StringIO())
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, [settings.OWNER_EMAIL])
        self.assertIn("deliberate-test-error", mail.outbox[0].subject)

    @override_settings(DEBUG=True)
    def test_refuses_where_nothing_would_be_sent(self):
        from django.core.management import call_command
        from django.core.management.base import CommandError

        with self.assertRaises(CommandError):
            call_command("test_error_report", stdout=StringIO())
