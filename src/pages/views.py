import logging

from django.conf import settings
from django.core.mail import send_mail
from django.shortcuts import render
from django.utils.translation import gettext as _
from django_ratelimit.core import is_ratelimited

from portfolio.models import Album
from timeline.models import TimelineEntry

from .forms import ContactForm
from .models import AboutSettings, ContactSettings, HomeSettings, PricingPackage, PricingSettings

logger = logging.getLogger(__name__)


def home(request):
    home_settings = HomeSettings.get_solo()
    context = {"home": home_settings}

    if home_settings.show_featured_album:
        context["featured_album"] = (
            Album.objects.visible().select_related("category").order_by("-id").first()
        )
    if home_settings.show_latest_timeline_entry:
        context["latest_entry"] = TimelineEntry.objects.visible().first()

    return render(request, "pages/home.html", context)


def about(request):
    return render(request, "pages/about.html", {"about": AboutSettings.get_solo()})


def pricing(request):
    return render(
        request,
        "pages/pricing.html",
        {
            "pricing": PricingSettings.get_solo(),
            "packages": PricingPackage.objects.filter(visible=True),
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
    form = ContactForm(request.POST or None)

    if request.method == "POST":
        # Counted per IP, before any work is done. Applied to POST only, so simply
        # reading the page is never rate limited.
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
        {"contact": settings_obj, "form": form, "sent": sent},
    )


def _client_ip(request):
    forwarded = request.META.get("HTTP_X_FORWARDED_FOR", "")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR")


def _notify_owner(submission):
    """Mail the submission to the owner. Returns whether the relay accepted it."""
    body = "\n".join(
        [
            f"Name:     {submission.name}",
            f"Email:    {submission.email}",
            f"Type:     {submission.shoot_type or '—'}",
            f"Date:     {submission.preferred_date or '—'}",
            f"IP:       {submission.ip_address or '—'}",
            "",
            submission.message,
        ]
    )
    try:
        send_mail(
            subject=f"Contact form: {submission.name}",
            message=body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[settings.OWNER_EMAIL],
            fail_silently=False,
        )
        return True
    except Exception:
        # The submission row is still written, so nothing is lost if the relay is down.
        logger.exception("Contact form email could not be delivered")
        return False
