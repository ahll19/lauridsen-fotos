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
