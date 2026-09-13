"""
Tests for the parts of client galleries where a mistake would be a privacy incident:
the password gate, cookie scoping, expiry, and the fact that files actually leave disk.
"""

from datetime import timedelta
from io import BytesIO

from django.conf import settings
from django.core.files.base import ContentFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

from .models import ClientGallery, GalleryPhoto


def tiny_jpeg(colour=(120, 110, 100)):
    buffer = BytesIO()
    Image.new("RGB", (60, 40), colour).save(buffer, format="JPEG")
    return ContentFile(buffer.getvalue(), name="test.jpg")


def make_gallery(password="correct-horse", days=30, photos=2):
    gallery = ClientGallery(
        label="Test gallery",
        expires_at=timezone.now() + timedelta(days=days),
    )
    gallery.set_password(password)
    gallery.save()
    for _ in range(photos):
        photo = GalleryPhoto(gallery=gallery)
        photo.image.save("photo.jpg", tiny_jpeg(), save=False)
        photo.save()
    return gallery


# X-Accel hands the file to nginx, which isn't present in tests; stream it instead so the
# response body is assertable.
@override_settings(USE_X_ACCEL=False)
class GalleryAccessTests(TestCase):
    def setUp(self):
        self.gallery = make_gallery()
        self.url = self.gallery.get_absolute_url()

    def test_password_prompt_shown_before_unlock(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "password", status_code=200)

    def test_no_photo_urls_leak_before_unlock(self):
        """The locked page must not disclose how many photographs exist, or their URLs."""
        response = self.client.get(self.url)
        for photo in self.gallery.photos.all():
            self.assertNotContains(
                response, reverse("galleries:photo", args=[self.gallery.slug, photo.pk])
            )

    def test_wrong_password_is_rejected_generically(self):
        response = self.client.post(self.url, {"password": "wrong"})
        self.assertEqual(response.status_code, 401)
        self.assertNotContains(response, "photo-grid", status_code=401)

    def test_correct_password_unlocks_and_persists(self):
        response = self.client.post(self.url, {"password": "correct-horse"})
        self.assertRedirects(response, self.url)

        # The cookie alone should carry the next request.
        page = self.client.get(self.url)
        self.assertEqual(page.status_code, 200)
        self.assertContains(page, "photo-grid")

    def test_photo_requires_unlock(self):
        photo = self.gallery.photos.first()
        url = reverse("galleries:photo", args=[self.gallery.slug, photo.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

        self.client.post(self.url, {"password": "correct-horse"})
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_download_requires_unlock(self):
        photo = self.gallery.photos.first()
        url = reverse("galleries:download_photo", args=[self.gallery.slug, photo.pk])
        self.assertEqual(self.client.get(url).status_code, 404)

    def test_cookie_does_not_transfer_between_galleries(self):
        """Unlocking one gallery must not unlock another."""
        other = make_gallery(password="different")
        self.client.post(self.url, {"password": "correct-horse"})

        response = self.client.get(other.get_absolute_url())
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "photo-grid")

    def test_gallery_is_not_indexable(self):
        response = self.client.get(self.url)
        self.assertIn("noindex", response["X-Robots-Tag"])

    def test_gallery_absent_from_sitemap(self):
        response = self.client.get("/sitemap.xml")
        self.assertNotContains(response, self.gallery.slug)

    def test_gallery_path_absent_from_robots(self):
        """Listing it would publish the URL pattern of private content."""
        response = self.client.get("/robots.txt")
        self.assertNotContains(response, "/g/")


@override_settings(USE_X_ACCEL=False)
class GalleryPrivacyHeaderTests(TestCase):
    """Private responses must not be storable by anything between here and the client."""

    def setUp(self):
        self.gallery = make_gallery()
        self.client_ = Client()
        self.client_.post(self.gallery.get_absolute_url(), {"password": "correct-horse"})

    def test_gallery_page_is_not_cacheable(self):
        response = self.client_.get(self.gallery.get_absolute_url())
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_photo_download_is_not_cacheable(self):
        photo = self.gallery.photos.first()
        response = self.client_.get(
            reverse("galleries:download_photo", args=[self.gallery.slug, photo.pk])
        )
        self.assertEqual(response["Cache-Control"], "private, no-store")

    def test_zip_is_named_for_the_gallery_not_the_url_key(self):
        """The client keeps this file; the URL key tells them nothing about it."""
        self.gallery.client_name = "Sofie & Jonas"
        self.gallery.save()
        self.gallery.build_zip()
        response = self.client_.get(reverse("galleries:download_zip", args=[self.gallery.slug]))
        self.assertIn("sofie-jonas.zip", response["Content-Disposition"])
        self.assertNotIn(self.gallery.slug, response["Content-Disposition"])


@override_settings(USE_X_ACCEL=False, GALLERY_UNLOCK_RATELIMIT="3/h")
class GalleryUnlockRateLimitTests(TestCase):
    def test_repeated_wrong_passwords_are_throttled(self):
        gallery = make_gallery()
        client = Client()
        for _ in range(3):
            client.post(gallery.get_absolute_url(), {"password": "wrong"})

        response = client.post(gallery.get_absolute_url(), {"password": "wrong"})
        self.assertEqual(response.status_code, 429)

    def test_throttling_does_not_reveal_the_correct_password(self):
        """Once throttled, even the right password is refused rather than accepted."""
        gallery = make_gallery()
        client = Client()
        for _ in range(4):
            client.post(gallery.get_absolute_url(), {"password": "wrong"})

        response = client.post(gallery.get_absolute_url(), {"password": "correct-horse"})
        self.assertEqual(response.status_code, 429)


@override_settings(USE_X_ACCEL=False)
class GalleryFileCleanupTests(TestCase):
    def test_bulk_delete_from_the_admin_removes_the_files(self):
        """
        The admin's "Delete selected" calls queryset.delete(), which skips Model.delete()
        — so the files were left behind for exactly the bulk case.
        """
        from django.contrib.admin.sites import AdminSite

        from galleries.admin import ClientGalleryAdmin

        gallery = make_gallery()
        directory = gallery.media_dir
        self.assertTrue(directory.exists())

        admin_instance = ClientGalleryAdmin(ClientGallery, AdminSite())
        admin_instance.delete_queryset(None, ClientGallery.objects.filter(pk=gallery.pk))

        self.assertFalse(directory.exists())
        self.assertEqual(ClientGallery.objects.count(), 0)


@override_settings(USE_X_ACCEL=False)
class GalleryExpiryTests(TestCase):
    def test_expired_gallery_shows_tombstone_not_content(self):
        gallery = make_gallery(days=-1)
        response = Client().get(gallery.get_absolute_url())
        self.assertEqual(response.status_code, 410)
        self.assertNotContains(response, "photo-grid", status_code=410)

    def test_correct_password_does_not_open_an_expired_gallery(self):
        gallery = make_gallery(days=-1)
        response = Client().post(gallery.get_absolute_url(), {"password": "correct-horse"})
        self.assertEqual(response.status_code, 410)

    def test_expire_now_removes_files_from_disk(self):
        gallery = make_gallery()
        directory = gallery.media_dir
        gallery.build_zip()

        self.assertTrue(directory.exists())
        self.assertTrue(gallery.zip_exists)

        gallery.expire_now()

        # A data-retention requirement, not a UI one: the bytes must be gone.
        self.assertFalse(directory.exists())
        self.assertEqual(gallery.photos.count(), 0)
        self.assertTrue(gallery.deleted)

    def test_expiry_command_only_touches_due_galleries(self):
        from django.core.management import call_command

        due = make_gallery(days=-1)
        not_due = make_gallery(days=10)

        call_command("expire_galleries", verbosity=0)

        due.refresh_from_db()
        not_due.refresh_from_db()
        self.assertTrue(due.deleted)
        self.assertFalse(not_due.deleted)

    def test_purge_removes_tombstones_past_retention(self):
        from django.core.management import call_command

        old = make_gallery(days=-400)
        old.expire_now()
        recent = make_gallery(days=-1)
        recent.expire_now()

        call_command("purge_tombstoned_galleries", verbosity=0)

        self.assertFalse(ClientGallery.objects.filter(pk=old.pk).exists())
        self.assertTrue(ClientGallery.objects.filter(pk=recent.pk).exists())


@override_settings(USE_X_ACCEL=False)
class GalleryLanguageTests(TestCase):
    """
    Galleries live outside the language-prefixed URLs, so the visitor's language choice
    has to be honoured from the cookie rather than from the path.
    """

    def setUp(self):
        self.gallery = make_gallery()
        self.url = self.gallery.get_absolute_url()

    def test_defaults_to_danish(self):
        response = self.client.get(self.url)
        self.assertContains(response, "Privat galleri")

    def test_english_cookie_is_honoured(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "en"
        response = self.client.get(self.url)
        self.assertContains(response, "Private gallery")
        self.assertNotContains(response, "Privat galleri")

    def test_switching_language_keeps_the_url_and_the_unlock(self):
        """The gallery link a client was given must keep working across a language change."""
        self.gallery.build_zip()
        self.client.post(self.url, {"password": "correct-horse"})
        self.assertContains(self.client.get(self.url), "photo-grid")

        # The page offers itself as the switch target, since the URL has no prefix.
        switch = self.client.post(reverse("set_language"), {"language": "en", "next": self.url})
        self.assertEqual(switch["Location"], self.url)

        response = self.client.get(self.url)
        self.assertContains(response, "photo-grid")
        self.assertContains(response, "Download all as ZIP")

    def test_an_invalid_language_cookie_is_ignored(self):
        self.client.cookies[settings.LANGUAGE_COOKIE_NAME] = "klingon"
        self.assertEqual(self.client.get(self.url).status_code, 200)


class GalleryModelTests(TestCase):
    def test_slug_is_unguessable_and_unique(self):
        slugs = {make_gallery(photos=0).slug for _ in range(20)}
        self.assertEqual(len(slugs), 20)
        self.assertTrue(all(len(slug) >= 20 for slug in slugs))

    def test_password_is_hashed_not_stored(self):
        gallery = make_gallery(password="plaintext-secret", photos=0)
        self.assertNotIn("plaintext-secret", gallery.password_hash)
        self.assertTrue(gallery.check_gallery_password("plaintext-secret"))
        self.assertFalse(gallery.check_gallery_password("something-else"))

    def test_zip_contains_every_photo(self):
        import zipfile

        gallery = make_gallery(photos=3)
        self.assertEqual(gallery.build_zip(), 3)
        with zipfile.ZipFile(gallery.zip_path) as archive:
            self.assertEqual(len(archive.namelist()), 3)
