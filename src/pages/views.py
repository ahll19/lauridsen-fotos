import logging

from django.conf import settings
from django.core.mail import EmailMessage
from django.shortcuts import render
from django.utils.translation import gettext as _
from django_ratelimit.core import is_ratelimited

from core.meta import page_meta
from portfolio.models import Album
from timeline.models import TimelineEntry

from .forms import ContactForm
from .models import AboutSettings, ContactSettings, HomeSettings, PricingPackage, PricingSettings

logger = logging.getLogger(__name__)


def home(request):
    home_settings = HomeSettings.get_solo()
    context = {
        "home": home_settings,
        **page_meta(
            request,
            description=home_settings.intro or home_settings.tagline,
            image=home_settings.hero_image,
        ),
    }

    if home_settings.show_featured_album:
        context["featured_album"] = (
            # Both the album and its category must be published, as on the album's own
            # page; otherwise an album prepared in a hidden category leaked onto the home
            # page and linked to a 404.
            Album.objects.visible()
            .filter(category__visible=True)
            .select_related("category")
            .order_by("-id")
            .first()
        )
    if home_settings.show_latest_timeline_entry:
        context["latest_entry"] = TimelineEntry.objects.visible().first()

    return render(request, "pages/home.html", context)


def about(request):
    about_settings = AboutSettings.get_solo()
    return render(
        request,
        "pages/about.html",
        {
            "about": about_settings,
            **page_meta(
                request,
                title=about_settings.heading or _("About"),
                description=about_settings.biography,
                image=about_settings.portrait,
            ),
        },
    )


def pricing(request):
    pricing_settings = PricingSettings.get_solo()
    return render(
        request,
        "pages/pricing.html",
        {
            "pricing": pricing_settings,
            "packages": PricingPackage.objects.filter(visible=True),
            **page_meta(
                request,
                title=pricing_settings.heading or _("Pricing"),
                description=pricing_settings.intro,
            ),
        },
    )


def contact(request):
    """
    The contact form.

    Result is shown inline on the same page rather than via a redirect, so the visitor
    always sees what happened to their message.
    """
    settings_obj = ContactSettings.get_solo()
    sent = False

    # The pricing page links here as ?type=<package name> so an enquiry arrives saying
    # which package prompted it. The link already carried the value; nothing read it.
    # Trimmed to the field's own length, and only ever an initial value — the visitor can
    # edit or clear it, and a bound POST ignores it entirely.
    initial = {}
    requested_type = request.GET.get("type", "").strip()
    if requested_type:
        initial["shoot_type"] = requested_type[:120]

    form = ContactForm(request.POST or None, initial=initial)

    if request.method == "POST":
        # Counted per IP, before any work is done. Applied to POST only, so simply
        # reading the page is never rate limited. Where every visitor arrives from one
        # address the count is for the whole site, and CONTACT_RATELIMIT is set to suit
        # (ADR 0014).
        limited = is_ratelimited(
            request,
            group="pages.contact",
            key="ip",
            rate=settings.CONTACT_RATELIMIT,
            method=["POST"],
            increment=True,
        )

        if limited:
            form.add_error(
                None,
                _("Too many messages have been sent from here recently. Please try again later."),
            )
        elif form.is_bot:
            # Silently accepted as far as the sender can tell; nothing is stored or sent.
            logger.info("Contact form honeypot triggered from %s", _client_ip(request))
            sent = True
            form = ContactForm()
        elif form.is_valid():
            submission = form.save(commit=False)
            submission.ip_address = _client_ip(request)
            submission.email_sent = _notify_owner(submission)
            submission.save()

            if submission.email_sent:
                sent = True
                form = ContactForm()
            else:
                form.add_error(
                    None,
                    _(
                        "Your message was received, but the confirmation email could not be "
                        "sent. Please get in touch directly if you don't hear back."
                    ),
                )

    return render(
        request,
        "pages/contact.html",
        {
            "contact": settings_obj,
            "form": form,
            "sent": sent,
            **page_meta(
                request,
                title=settings_obj.heading or _("Contact"),
                description=settings_obj.intro,
            ),
        },
    )


def _client_ip(request):
    """
    ClientIPMiddleware has already resolved this out of X-Forwarded-For.

    Reading the header here instead would take its left-most entry, which is whatever the
    caller chose to send — so the recorded address of an abusive sender would be one they
    picked themselves.
    """
    return request.META.get("REMOTE_ADDR")


def _notify_owner(submission):
    """Mail the submission to the owner. Returns whether the relay accepted it."""
    body = "\n".join(
        [
            f"{_('Name:')} {submission.name}",
            f"{_('Email:')} {submission.email}",
            f"{_('Type:')} {submission.shoot_type or '—'}",
            f"{_('Date:')} {submission.preferred_date or '—'}",
            f"{_('IP address:')} {submission.ip_address or '—'}",
            "",
            submission.message,
        ]
    )
    message = EmailMessage(
        subject=_("Contact form: %(name)s") % {"name": submission.name},
        body=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        to=[settings.OWNER_EMAIL],
        # So replying in the mail client answers the enquirer rather than the no-reply
        # address the relay sends as. The address is validated by the form.
        reply_to=[submission.email],
    )
    try:
        message.send(fail_silently=False)
        return True
    except Exception:
        # The submission row is still written, so nothing is lost if the relay is down.
        logger.exception("Contact form email could not be delivered")
        return False
