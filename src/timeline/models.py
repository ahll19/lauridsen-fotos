from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from ordered_model.models import OrderedModel


class TimelineEntryQuerySet(models.QuerySet):
    def visible(self):
        return self.filter(visible=True)


class TimelineEntry(models.Model):
    """A showcase/creative session — deliberately photo-led, not an article."""

    title = models.CharField(_("title"), max_length=180)
    slug = models.SlugField(_("slug"), max_length=200, unique=True)
    date = models.DateField(_("date"))
    caption = models.TextField(
        _("caption"),
        blank=True,
        help_text=_("A short story about the session — a paragraph or two, not an article."),
    )
    tags = models.CharField(
        _("tags"),
        max_length=200,
        blank=True,
        help_text=_("Comma-separated, e.g. winter, coast, film."),
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
        return [tag.strip() for tag in self.tags.split(",") if tag.strip()]


def timeline_photo_path(instance, filename):
    return f"timeline/{instance.entry.slug}/{filename}"


class TimelineEntryPhoto(OrderedModel):
    entry = models.ForeignKey(
        TimelineEntry, on_delete=models.CASCADE, related_name="photos", verbose_name=_("entry")
    )
    image = models.ImageField(_("image"), upload_to=timeline_photo_path)
    caption = models.CharField(_("caption"), max_length=240, blank=True)

    order_with_respect_to = "entry"

    class Meta(OrderedModel.Meta):
        verbose_name = _("timeline photo")
        verbose_name_plural = _("timeline photos")

    def __str__(self):
        return self.caption or self.image.name.rsplit("/", 1)[-1]
