"""
Private file delivery.

Django decides whether the caller may have the file; nginx moves the bytes. The file's
real location is never a URL anyone can request directly — nginx's `internal` flag means
only an X-Accel-Redirect header from this application can route into it.
"""

from pathlib import Path
from urllib.parse import quote

from django.conf import settings
from django.http import FileResponse, Http404, HttpResponse


def protected_file_response(path, *, filename=None, content_type=None, as_attachment=False):
    """
    Serve a file living under DATA_ROOT without exposing where it is.

    Falls back to streaming through Django when X-Accel is switched off, which is what
    makes `manage.py runserver` and the test suite work without nginx in front.
    """
    path = Path(path)
    data_root = Path(settings.DATA_ROOT).resolve()

    try:
        resolved = path.resolve(strict=True)
    except OSError as exc:
        raise Http404("File not found") from exc

    # Refuse anything that resolves outside the data directory, whatever built the path.
    if not resolved.is_relative_to(data_root):
        raise Http404("File not found")

    if not settings.USE_X_ACCEL:
        return FileResponse(
            open(resolved, "rb"),
            as_attachment=as_attachment,
            filename=filename or resolved.name,
            content_type=content_type,
        )

    response = HttpResponse(content_type=content_type or "")
    internal = settings.X_ACCEL_PREFIX + str(resolved.relative_to(data_root))
    response["X-Accel-Redirect"] = quote(internal)

    # Let nginx determine the type and length from the file itself.
    if not content_type:
        del response["Content-Type"]

    if as_attachment:
        name = filename or resolved.name
        response["Content-Disposition"] = f'attachment; filename="{name}"'

    return response


def noindex(response):
    """Keep a response out of search indexes without advertising its URL in robots.txt."""
    response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    return response
