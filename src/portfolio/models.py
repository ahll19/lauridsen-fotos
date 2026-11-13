from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from ordered_model.models import OrderedModel, OrderedModelManager, OrderedModelQuerySet

from core.text import LINK_HELP


class VisibleQuerySet(OrderedModelQuerySet):
    def visible(self):
        return self.filter(visible=True)


class CategoryQuerySet(VisibleQuerySet):
    def published(self):
        """
        Visible, with at least one visible album: what the public site lists.

        A visible category with nothing public in it showed as an empty heading on the
        portfolio page. It appears by itself once its first album is published.
        """
        return self.visible().filter(albums__visible=True).distinct()


# Must keep the ordering manager's behaviour, or move up/down in the admin breaks.
VisibleManager = OrderedModelManager.from_queryset(VisibleQuerySet)
CategoryManager = OrderedModelManager.from_queryset(CategoryQuerySet)


class Category(OrderedModel):
    """A top-level grouping of albums, e.g. Weddings or Portraits."""

    name = models.CharField(_("name"), max_length=120)
    slug = models.SlugField(_("slug"), max_length=140, unique=True)
    description = models.TextField(_("description"), blank=True, help_text=LINK_HELP)
    visible = models.BooleanField(
        _("visible"),
        default=False,
        help_text=_("Unpublished categories are hidden from the public site."),
    )

    objects = CategoryManager()

    class Meta(OrderedModel.Meta):
        verbose_name = _("category")
        verbose_name_plural = _("categories")

    def __str__(self):
        return self.name

    def get_absolute_url(self):
        return reverse("portfolio:category", args=[self.slug])

    def visible_albums(self):
        return self.albums.visible()


def album_cover_path(instance, filename):
    return f"portfolio/{instance.category.slug}/{instance.slug}/cover/{filename}"


class Album(OrderedModel):
    """A curated set of photographs within a category."""

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, related_name="albums", verbose_name=_("category")
    )
    name = models.CharField(_("name"), max_length=160)
    slug = models.SlugField(_("slug"), max_length=180)
    description = models.TextField(_("description"), blank=True, help_text=LINK_HELP)
    cover = models.ImageField(_("cover image"), upload_to=album_cover_path, blank=True)
    visible = models.BooleanField(
        _("visible"),
        default=False,
        help_text=_("Unpublished albums are hidden from the public site."),
    )

    objects = VisibleManager()
    order_with_respect_to = "category"

    class Meta(OrderedModel.Meta):
        verbose_name = _("album")
        verbose_name_plural = _("albums")
        constraints = [
            models.UniqueConstraint(
                fields=["category", "slug"], name="unique_album_slug_per_category"
            )
        ]

    def __str__(self):
        return f"{self.category.name} — {self.name}"

    def get_absolute_url(self):
        return reverse("portfolio:album", args=[self.category.slug, self.slug])

    @property
    def cover_image(self):
        """The album's own cover, or its first photo as a stand-in."""
        if self.cover:
            return self.cover
        first = self.photos.first()
        return first.image if first else None


def photo_path(instance, filename):
    album = instance.album
    return f"portfolio/{album.category.slug}/{album.slug}/{filename}"


class Photo(OrderedModel):
    album = models.ForeignKey(
        Album, on_delete=models.CASCADE, related_name="photos", verbose_name=_("album")
    )
    image = models.ImageField(_("image"), upload_to=photo_path)
    caption = models.CharField(_("caption"), max_length=240, blank=True)
    alt_text = models.CharField(
        _("alt text"),
        max_length=240,
        blank=True,
        help_text=_(
            "Describes what is in the photograph, for visitors who cannot see it and for "
            "search engines. Not shown on the page. The caption is used if this is empty."
        ),
    )

    order_with_respect_to = "album"

    class Meta(OrderedModel.Meta):
        verbose_name = _("photo")
        verbose_name_plural = _("photos")

    def __str__(self):
        return self.caption or self.image.name.rsplit("/", 1)[-1]

    @property
    def alt(self):
        """A caption is shown and an alt text describes; fall back rather than say nothing."""
        return self.alt_text or self.caption
