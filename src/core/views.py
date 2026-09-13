from django.db import connection
from django.http import HttpResponse
from django.views.decorators.cache import never_cache


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
