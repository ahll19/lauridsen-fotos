import logging
import secrets
import shutil
import zipfile
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.contrib.auth.hashers import check_password, make_password
from django.db import models
from django.urls import reverse
from django.utils import timezone
from django.utils.translation import gettext_lazy as _
from ordered_model.models import OrderedModel

logger = logging.getLogger(__name__)

# Long enough that guessing is hopeless, short enough to paste into a message.
SLUG_BYTES = 16
PASSWORD_WORDS_BYTES = 9


def generate_slug():
    return secrets.token_urlsafe(SLUG_BYTES)


def generate_password():
    return secrets.token_urlsafe(PASSWORD_WORDS_BYTES)


def default_expiry():
    return timezone.now() + timedelta(days=settings.GALLERY_DEFAULT_EXPIRY_DAYS)


class ClientGalleryQuerySet(models.QuerySet):
    def live(self):
        """Galleries that still hold photographs."""
        return self.filter(deleted=False)

    def due_for_expiry(self, now=None):
        now = now or timezone.now()
        return self.filter(deleted=False, expires_at__lte=now)

    def due_for_purge(self, now=None):
        now = now or timezone.now()
        cutoff = now - timedelta(days=settings.GALLERY_TOMBSTONE_RETENTION_DAYS)
        return self.filter(deleted=True, expires_at__lte=cutoff)


class ClientGallery(models.Model):
    """
    A private delivery gallery for one client.

    Reached only by its unguessable URL plus a password. Deletes its own files once it
    expires, then survives as a tombstone for a while so the URL can say so rather than
    404 (technical_design.md §8).
    """

    slug = models.SlugField(
        _("URL key"),
        max_length=64,
        unique=True,
        default=generate_slug,
        help_text=_("Generated. This is the unguessable part of the gallery's link."),
    )
    label = models.CharField(
        _("label"),
        max_length=160,
        help_text=_(
            "Your own reference, e.g. 'Sofie & Jonas, June wedding'. Never shown to the client."
        ),
    )
    client_name = models.CharField(
        _("client name"),
        max_length=160,
        blank=True,
        help_text=_("Shown as a greeting on the gallery page. Optional."),
    )
    password_hash = models.CharField(_("password hash"), max_length=256, editable=False)
    created_at = models.DateTimeField(_("created"), auto_now_add=True)
    expires_at = models.DateTimeField(
        _("expires"),
        default=default_expiry,
        help_text=_("After this date the photographs are deleted from disk automatically."),
    )
    deleted = models.BooleanField(
        _("photos deleted"),
        default=False,
        editable=False,
        help_text=_("Set by the expiry job once the files have been removed."),
    )
    zip_built_at = models.DateTimeField(_("ZIP built"), null=True, blank=True, editable=False)

    objects = ClientGalleryQuerySet.as_manager()

    class Meta:
        verbose_name = _("client gallery")
        verbose_name_plural = _("client galleries")
        ordering = ["-created_at"]

    def __str__(self):
        return self.label

    def get_absolute_url(self):
        return reverse("galleries:detail", args=[self.slug])

    # --- Passwords -----------------------------------------------------------

    def set_password(self, raw=None):
        """Store a hash and hand back the plaintext, which is never recoverable later."""
        raw = raw or generate_password()
        self.password_hash = make_password(raw)
        return raw

    def check_gallery_password(self, raw):
        return bool(raw) and check_password(raw, self.password_hash)

    # --- Lifecycle -----------------------------------------------------------

    @property
    def is_expired(self):
        return timezone.now() >= self.expires_at

    @property
    def is_available(self):
        """Whether a visitor with the password should see photographs."""
        return not self.deleted and not self.is_expired

    @property
    def days_remaining(self):
        return max(0, (self.expires_at - timezone.now()).days)

    # --- Files ---------------------------------------------------------------

    @property
    def media_dir(self) -> Path:
        return Path(settings.MEDIA_ROOT) / "galleries" / self.slug

    @property
    def zip_path(self) -> Path:
        return self.media_dir / f"{self.slug}.zip"

    @property
    def zip_exists(self):
        return self.zip_path.exists()

    def build_zip(self):
        """
        Build the full-album ZIP once, explicitly.

        Deliberately not done on save: re-zipping a wedding's worth of full-resolution
        files on every minor edit would be wasteful.
        """
        photos = list(self.photos.all())
        if not photos:
            return 0

        self.media_dir.mkdir(parents=True, exist_ok=True)
        tmp_path = self.zip_path.with_suffix(".zip.tmp")

        with zipfile.ZipFile(tmp_path, "w", zipfile.ZIP_STORED) as archive:
            for index, photo in enumerate(photos, start=1):
                source = Path(photo.image.path)
                if not source.exists():
                    logger.warning("Gallery %s: missing file %s", self.slug, source)
                    continue
                # Numbered so the client's file manager preserves the curated order.
                archive.write(source, arcname=f"{index:03d}_{source.name}")

        # Atomic swap, so a client downloading during a rebuild never gets a partial file.
        tmp_path.replace(self.zip_path)
        self.zip_built_at = timezone.now()
        self.save(update_fields=["zip_built_at"])
        return len(photos)

    def delete_files(self):
        """Remove every byte belonging to this gallery, including the built ZIP."""
        directory = self.media_dir
        if directory.exists():
            shutil.rmtree(directory)
            logger.info("Gallery %s: deleted %s", self.slug, directory)
            return True
        return False

    def expire_now(self):
        """Delete the files and leave a tombstone behind."""
        self.delete_files()
        count = self.photos.count()
        self.photos.all().delete()
        self.deleted = True
        self.zip_built_at = None
        self.save(update_fields=["deleted", "zip_built_at"])
        return count

    def delete(self, *args, **kwargs):
        # Deleting from the admin should not leave orphaned files on disk.
        self.delete_files()
        return super().delete(*args, **kwargs)


def gallery_photo_path(instance, filename):
    return f"galleries/{instance.gallery.slug}/{filename}"


class GalleryPhoto(OrderedModel):
    gallery = models.ForeignKey(
        ClientGallery, on_delete=models.CASCADE, related_name="photos", verbose_name=_("gallery")
    )
    image = models.ImageField(_("image"), upload_to=gallery_photo_path)

    order_with_respect_to = "gallery"

    class Meta(OrderedModel.Meta):
        verbose_name = _("gallery photo")
        verbose_name_plural = _("gallery photos")

    def __str__(self):
        return self.image.name.rsplit("/", 1)[-1]

    @property
    def filename(self):
        return self.image.name.rsplit("/", 1)[-1]
