import datetime
import re

from django import forms
from django.core import mail
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import translation

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


class DateFormatTests(TestCase):
    """Dates are day first in both languages (config/formats/day_first.py)."""

    def test_forms_show_and_accept_day_first_dates_in_both_languages(self):
        class DateForm(forms.Form):
            day = forms.DateField()

        for language in ("da", "en"):
            with self.subTest(language=language), translation.override(language):
                shown = DateForm(initial={"day": datetime.date(2026, 11, 3)})
                self.assertIn('value="03/11/2026"', str(shown["day"]))
                typed = DateForm({"day": "03/11/2026"})
                self.assertTrue(typed.is_valid())
                self.assertEqual(typed.cleaned_data["day"], datetime.date(2026, 11, 3))

    def test_contact_form_keeps_the_date_in_the_form_a_date_picker_reads(self):
        """A rejected submission is shown again; a picker given 03/11/2026 shows nothing."""
        response = self.client.post(
            reverse("pages:contact"),
            {"name": "", "email": "s@example.com", "message": "Hi", "preferred_date": "2026-11-03"},
        )
        self.assertContains(response, 'value="2026-11-03"')


class FrontPageTeaserTests(TestCase):
    """The random mix of albums and timeline entries under the front page's main image."""

    def _image(self):
        from io import BytesIO

        from django.core.files.uploadedfile import SimpleUploadedFile
        from PIL import Image

        buffer = BytesIO()
        Image.new("RGB", (30, 20), (90, 90, 90)).save(buffer, "JPEG")
        return SimpleUploadedFile("p.jpg", buffer.getvalue(), content_type="image/jpeg")

    def _album(self, slug, category, visible=True, photo=True):
        from portfolio.models import Album, Photo

        album = Album.objects.create(category=category, name=slug, slug=slug, visible=visible)
        if photo:
            Photo.objects.create(album=album, image=self._image())
        return album

    def _entry(self, slug, visible=True, photo=True):
        from timeline.models import TimelineEntry, TimelineEntryPhoto

        entry = TimelineEntry.objects.create(
            slug=slug, title_da=slug, date=datetime.date(2026, 1, 1), visible=visible
        )
        if photo:
            TimelineEntryPhoto.objects.create(entry=entry, image=self._image())
        return entry

    def setUp(self):
        from portfolio.models import Category

        self.shown = Category.objects.create(name="Shown", slug="shown", visible=True)
        self.hidden = Category.objects.create(name="Hidden", slug="hidden", visible=False)

    def teasers(self):
        return self.client.get(reverse("pages:home")).context["teasers"]

    def test_albums_and_entries_alternate(self):
        for n in range(3):
            self._album(f"album-{n}", self.shown)
            self._entry(f"entry-{n}")
        kinds = ["/portfolio/" in t["url"] for t in self.teasers()]
        self.assertEqual(kinds, [True, False, True, False, True, False])

    def test_nothing_appears_twice_and_never_more_than_eight(self):
        for n in range(7):
            self._album(f"album-{n}", self.shown)
            self._entry(f"entry-{n}")
        urls = [t["url"] for t in self.teasers()]
        self.assertEqual(len(urls), 8)
        self.assertEqual(len(set(urls)), 8)

    def test_one_kind_fills_in_when_the_other_runs_out(self):
        self._album("only-album", self.shown)
        for n in range(4):
            self._entry(f"entry-{n}")
        self.assertEqual(len(self.teasers()), 5)

    def test_only_published_work_with_a_picture_is_used(self):
        self._album("published", self.shown)
        self._album("draft", self.shown, visible=False)
        self._album("in-hidden-category", self.hidden)
        self._album("no-photos", self.shown, photo=False)
        self._entry("entry")
        self._entry("draft-entry", visible=False)
        self._entry("no-photos-entry", photo=False)
        urls = sorted(t["url"] for t in self.teasers())
        self.assertEqual(urls, ["/portfolio/shown/published/", "/timeline/entry/"])

    def test_each_kind_can_be_switched_off(self):
        from .models import HomeSettings

        self._album("album", self.shown)
        self._entry("entry")
        HomeSettings.objects.update_or_create(pk=1, defaults={"show_featured_album": False})
        self.assertEqual([t["url"] for t in self.teasers()], ["/timeline/entry/"])

    def test_front_page_renders_the_teasers(self):
        self._album("album", self.shown)
        response = self.client.get(reverse("pages:home"))
        self.assertContains(response, 'class="teaser"', count=1)


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
