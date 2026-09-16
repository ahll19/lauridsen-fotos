import logging

from django.db import connection
from django.http import HttpResponse
from django.shortcuts import render
from django.views.decorators.cache import never_cache

logger = logging.getLogger(__name__)


@never_cache
def healthz(request):
    """Liveness probe for the container healthcheck and the external uptime checker."""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:  # pragma: no cover - only on a genuinely broken database
        return HttpResponse("database unavailable", status=503, content_type="text/plain")
    return HttpResponse("ok", content_type="text/plain")


def robots_txt(request):
    """
    Client galleries are deliberately absent.

    Listing them under Disallow would publish the URL pattern of private content to
    anyone who reads this file, which is the opposite of what it is for. They are kept out
    of the sitemap and carry X-Robots-Tag: noindex instead (technical_design.md §8).
    """
    lines = [
        "User-agent: *",
        "Allow: /",
        "",
        f"Sitemap: {request.build_absolute_uri('/sitemap.xml')}",
    ]
    return HttpResponse("\n".join(lines), content_type="text/plain")


def csrf_failure(request, reason=""):
    """
    Render the site's own 403 page when a CSRF check fails.

    Django's default handler for this is django.views.csrf.csrf_failure, which renders a
    separate 403_csrf.html and — importantly — renders it with no request and no context
    processors, so it cannot use the site's own layout. Without this the one 403 the site
    actually produces was the unstyled built-in page, and 403.html was never reached.

    The reason is deliberately not shown. It is either "no CSRF cookie" or "referer
    mismatch", neither of which means anything to a visitor whose real problem is that the
    form sat open too long, and the template says what to do instead.
    """
    logger.warning("CSRF verification failed (%s) for %s", reason, request.path)
    return render(request, "403.html", status=403)
