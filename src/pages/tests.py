import re

from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse

from .models import ContactSubmission


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ContactFormTests(TestCase):
    def setUp(self):
        self.url = reverse("pages:contact")
        self.valid = {
            "name": "Sofie Hansen",
            "email": "sofie@example.com",
            "message": "Hi, are you free in June?",
            "shoot_type": "",
            "preferred_date": "",
            "website": "",
        }

    def test_pricing_link_prefills_the_shoot_type(self):
        """
        The pricing page links here as ?type=<package>, so an enquiry says which package
        prompted it. The link existed before the view read it.
        """
        response = self.client.get(self.url, {"type": "Bryllup — hel dag"})
        self.assertContains(response, 'value="Bryllup — hel dag"')

    def test_shoot_type_is_empty_without_the_parameter(self):
        response = self.client.get(self.url)
        self.assertNotContains(response, 'name="shoot_type" value=')

    def test_prefill_is_only_an_initial_value(self):
        """What the visitor actually submits wins over the query string."""
        data = dict(self.valid, shoot_type="Portræt")
        self.client.post(self.url + "?type=Bryllup", data)
        self.assertEqual(ContactSubmission.objects.get().shoot_type, "Portræt")

    def test_valid_submission_emails_owner_and_is_recorded(self):
        response = self.client.post(self.url, self.valid)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("Sofie Hansen", mail.outbox[0].body)

        submission = ContactSubmission.objects.get()
        self.assertEqual(submission.email, "sofie@example.com")
        self.assertTrue(submission.email_sent)

    def test_honeypot_submission_is_dropped_silently(self):
        """A filled honeypot looks successful to the sender but stores and sends nothing."""
        response = self.client.post(self.url, {**self.valid, "website": "http://spam.example"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(mail.outbox), 0)
        self.assertEqual(ContactSubmission.objects.count(), 0)

    def test_invalid_submission_reports_errors(self):
        response = self.client.post(self.url, {**self.valid, "email": "not-an-email"})
        self.assertEqual(len(mail.outbox), 0)
        self.assertContains(response, "field--error")

    @override_settings(CONTACT_RATELIMIT="2/h")
    def test_submissions_are_rate_limited_per_ip(self):
        for _ in range(2):
            self.client.post(self.url, self.valid)
        self.assertEqual(len(mail.outbox), 2)

        response = self.client.post(self.url, self.valid)

        # Asserted on behaviour rather than on the wording, which is translated: the
        # message is refused, nothing is sent, and nothing is recorded.
        self.assertEqual(len(mail.outbox), 2, "a rate-limited submission must not send mail")
        self.assertEqual(ContactSubmission.objects.count(), 2)
        self.assertContains(response, "notice--error")

    def test_submission_is_kept_even_when_mail_fails(self):
        """Mail can fail; the record of what a visitor sent should survive it."""
        with override_settings(EMAIL_BACKEND="django.core.mail.backends.dummy.EmailBackend"):
            with self.settings(EMAIL_HOST="127.0.0.1", EMAIL_PORT=1):
                self.client.post(self.url, self.valid)
        self.assertEqual(ContactSubmission.objects.count(), 1)


class PublicPageTests(TestCase):
    def test_every_navigation_page_responds(self):
        for name in [
            "pages:home",
            "pages:pricing",
            "pages:contact",
            "pages:about",
            "portfolio:index",
            "timeline:index",
        ]:
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)

    def test_health_check_responds(self):
        response = self.client.get("/healthz")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"ok")

    def test_language_can_be_switched(self):
        response = self.client.post(
            reverse("set_language"), {"language": "en", "next": "/"}, follow=True
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.cookies["django_language"].value, "en")


class LanguageRoundTripTests(TestCase):
    """
    Switching must work in both directions, on every page.

    Danish is the default and carries no URL prefix, so the language of a page is decided
    by its URL rather than by the cookie. Switching therefore has to land the visitor on
    the right URL — setting the cookie alone leaves them where they were.
    """

    def _offered_target(self, html, language_code):
        """The URL the rendered page offers for switching to a language."""
        pattern = (
            rf'<input type="hidden" name="language" value="{language_code}">\s*'
            r'<input type="hidden" name="next" value="([^"]*)">'
        )
        match = re.search(pattern, html)
        self.assertIsNotNone(match, f"no language form for {language_code!r} on the page")
        return match.group(1)

    def _switch(self, language_code, page_url):
        page = self.client.get(page_url)
        self.assertEqual(page.status_code, 200)
        target = self._offered_target(page.content.decode(), language_code)
        response = self.client.post(
            reverse("set_language"), {"language": language_code, "next": target}
        )
        return response["Location"]

    def test_da_to_en_and_back_again(self):
        """The bug: going back to Danish left the visitor on the English URL."""
        self.assertEqual(self._switch("en", "/"), "/en/")
        self.assertEqual(self._switch("da", "/en/"), "/")

        page = self.client.get("/")
        self.assertContains(page, '<html lang="da"')

    def test_round_trip_keeps_the_visitor_on_the_same_page(self):
        for danish_url, english_url in [
            ("/portfolio/", "/en/portfolio/"),
            ("/priser/", "/en/pricing/"),
            ("/kontakt/", "/en/contact/"),
            ("/timeline/", "/en/timeline/"),
        ]:
            with self.subTest(page=danish_url):
                self.assertEqual(self._switch("en", danish_url), english_url)
                self.assertEqual(self._switch("da", english_url), danish_url)

    def test_query_string_survives_the_switch(self):
        self.assertEqual(self._switch("en", "/timeline/?tag=vinter"), "/en/timeline/?tag=vinter")
