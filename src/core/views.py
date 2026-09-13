from django.conf import settings
from django.db import connection
from django.http import Http404, HttpResponse
from django.shortcuts import redirect, render
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_POST

from . import themes


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


# --- Design preview (temporary, ROADMAP 0.2.0) -------------------------------


def _require_preview():
    if not settings.DESIGN_PREVIEW_ENABLED:
        raise Http404("Design preview is not enabled")


@never_cache
def design_index(request):
    """Side-by-side descriptions of the candidate directions, with links into the real site."""
    _require_preview()
    return render(
        request,
        "core/design_index.html",
        {
            "candidates": themes.THEMES,
            "active": themes.get(request.COOKIES.get(settings.THEME_COOKIE_NAME)),
        },
    )


@require_POST
def design_choose(request):
    """Remember a direction for this browser and return to where the switch was made."""
    _require_preview()

    slug = request.POST.get("theme", "")
    target = request.POST.get("next") or "/"
    # Only ever redirect within this site.
    if not target.startswith("/") or target.startswith("//"):
        target = "/"

    response = redirect(target)
    if slug in themes.BY_SLUG:
        response.set_cookie(
            settings.THEME_COOKIE_NAME, slug, max_age=60 * 60 * 24 * 30, samesite="Lax"
        )
    else:
        response.delete_cookie(settings.THEME_COOKIE_NAME)
    return response
