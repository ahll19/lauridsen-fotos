from django.db import models
from django.db.models.functions import Lower
from django.urls import reverse
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from ordered_model.models import OrderedModel

from core.text import LINK_HELP


class TimelineEntryQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(visible=True)


class Tag(models.Model):
    """
    A word timeline entries are filtered by, chosen from one shared list.

    Free text spelled the same idea several ways over the years; a list to pick from, and
    names that differ only in case counting as the same tag, keeps it to one spelling.
    """

    name = models.CharField(_("name"), max_length=60)

    class Meta:
        verbose_name = _("tag")
        verbose_name_plural = _("tags")
        ordering = [Lower("name")]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="unique_tag_name_ignoring_case",
                violation_error_message=_("A tag with this name already exists."),
            )
        ]

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        self.name = " ".join(self.name.split())
        super().save(*args, **kwargs)


class TimelineEntry(models.Model):
    """A showcase/creative session — deliberately photo-led, not an article."""

    title = models.CharField(_("title"), max_length=180)
    slug = models.SlugField(_("slug"), max_length=200, unique=True)
    date = models.DateField(_("date"))
    caption = models.TextField(
        _("caption"),
        blank=True,
        help_text=format_lazy(
            "{} {}",
            _("A short story about the session — a paragraph or two, not an article."),
            LINK_HELP,
        ),
    )
    tags = models.ManyToManyField(
        "Tag",
        blank=True,
        related_name="entries",
        verbose_name=_("tags"),
        help_text=_("Choose from the tags already used; the + adds a new one."),
    )
    related_category = models.ForeignKey(
        "portfolio.Category",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="timeline_entries",
        verbose_name=_("related portfolio category"),
    )
    visible = models.BooleanField(_("visible"), default=False)

    objects = TimelineEntryQuerySet.as_manager()

    class Meta:
        verbose_name = _("timeline entry")
        verbose_name_plural = _("timeline entries")
        ordering = ["-date", "-id"]

    def __str__(self):
        return self.title

    def get_absolute_url(self):
        return reverse("timeline:entry", args=[self.slug])

    def tag_list(self):
        return [tag.name for tag in self.tags.all()]


def timeline_photo_path(instance, filename):
    return f"timeline/{instance.entry.slug}/{filename}"


class TimelineEntryPhoto(OrderedModel):
    entry = models.ForeignKey(
        TimelineEntry, on_delete=models.CASCADE, related_name="photos", verbose_name=_("entry")
    )
    image = models.ImageField(_("image"), upload_to=timeline_photo_path)
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

    order_with_respect_to = "entry"

    class Meta(OrderedModel.Meta):
        verbose_name = _("timeline photo")
        verbose_name_plural = _("timeline photos")

    def __str__(self):
        return self.caption or self.image.name.rsplit("/", 1)[-1]

    @property
    def alt(self):
        """A caption is shown and an alt text describes; fall back rather than say nothing."""
        return self.alt_text or self.caption
