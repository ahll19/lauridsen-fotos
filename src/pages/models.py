from django.db import models
from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _
from ordered_model.models import OrderedModel
from solo.models import SingletonModel

from core.text import LINK_HELP


class HomeSettings(SingletonModel):
    """The curated landing page. One instance, edited in place."""

    hero_image = models.ImageField(_("hero image"), upload_to="pages/home/", blank=True)
    business_name = models.CharField(_("business name"), max_length=120, default="Lauridsen Fotos")
    tagline = models.CharField(_("tagline"), max_length=240, blank=True)
    intro = models.TextField(_("introduction"), blank=True, help_text=LINK_HELP)
    show_featured_album = models.BooleanField(
        _("show albums on the front page"),
        default=True,
        help_text=_(
            "The front page shows a random mix of published albums and timeline entries, "
            "drawn afresh on every visit."
        ),
    )
    show_latest_timeline_entry = models.BooleanField(
        _("show timeline entries on the front page"), default=True
    )

    class Meta:
        verbose_name = _("home page")

    def __str__(self):
        return str(_("Home page"))


class AboutSettings(SingletonModel):
    portrait = models.ImageField(_("portrait"), upload_to="pages/about/", blank=True)
    heading = models.CharField(_("heading"), max_length=180, blank=True)
    biography = models.TextField(_("biography"), blank=True, help_text=LINK_HELP)
    how_i_work = models.TextField(_("how I work"), blank=True, help_text=LINK_HELP)

    class Meta:
        verbose_name = _("about page")

    def __str__(self):
        return str(_("About page"))


class ContactSettings(SingletonModel):
    heading = models.CharField(_("heading"), max_length=180, blank=True)
    intro = models.TextField(_("introduction"), blank=True, help_text=LINK_HELP)
    email = models.EmailField(_("public email address"), blank=True)
    phone = models.CharField(_("phone"), max_length=40, blank=True)
    instagram_url = models.URLField(_("Instagram"), blank=True)
    facebook_url = models.URLField(_("Facebook"), blank=True)

    class Meta:
        verbose_name = _("contact page")

    def __str__(self):
        return str(_("Contact page"))


class PricingSettings(SingletonModel):
    heading = models.CharField(_("heading"), max_length=180, blank=True)
    intro = models.TextField(_("introduction"), blank=True, help_text=LINK_HELP)
    faq = models.TextField(
        _("FAQ / how booking works"),
        blank=True,
        help_text=format_lazy("{} {}", _("Shown beneath the packages."), LINK_HELP),
    )

    class Meta:
        verbose_name = _("pricing page")

    def __str__(self):
        return str(_("Pricing page"))


class PricingPackage(OrderedModel):
    name = models.CharField(_("name"), max_length=140)
    description = models.TextField(
        _("what's included"), help_text=_("One item per line; rendered as a list.")
    )
    price = models.CharField(
        _("price"),
        max_length=60,
        help_text=_("Free text so the currency and any 'from' wording stay editable."),
    )
    visible = models.BooleanField(_("visible"), default=True)

    class Meta(OrderedModel.Meta):
        verbose_name = _("pricing package")
        verbose_name_plural = _("pricing packages")

    def __str__(self):
        return self.name

    def inclusions(self):
        return [line.strip() for line in self.description.splitlines() if line.strip()]


class ContactSubmission(models.Model):
    """
    A record of every contact-form submission.

    Not required by the functional design, but a cheap audit trail — mail can be lost or
    filtered, and this survives that.
    """

    name = models.CharField(_("name"), max_length=160)
    email = models.EmailField(_("email"))
    shoot_type = models.CharField(_("shoot type"), max_length=120, blank=True)
    preferred_date = models.DateField(_("preferred date"), null=True, blank=True)
    message = models.TextField(_("message"))
    submitted_at = models.DateTimeField(_("submitted at"), auto_now_add=True)
    ip_address = models.GenericIPAddressField(_("IP address"), null=True, blank=True)
    email_sent = models.BooleanField(
        _("notification sent"),
        default=False,
        help_text=_("False means the relay rejected it — the submission is still recorded here."),
    )

    class Meta:
        verbose_name = _("contact submission")
        verbose_name_plural = _("contact submissions")
        ordering = ["-submitted_at"]

    def __str__(self):
        return f"{self.name} <{self.email}> ({self.submitted_at:%Y-%m-%d})"
