"""
Private file delivery.

Django decides whether the caller may have the file; nginx moves the bytes. The file's
real location is never a URL anyone can request directly — nginx's `internal` flag means
only an X-Accel-Redirect header from this application can route into it.
"""

import unicodedata
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
        response["Content-Disposition"] = content_disposition(filename or resolved.name)

    return response


def content_disposition(filename):
    """
    An attachment header that survives a non-ASCII filename.

    Danish filenames routinely contain æ, ø and å, and a raw f-string leaves Django to
    MIME-encode the header into something browsers show verbatim. RFC 6266 handles this
    with a percent-encoded `filename*`, alongside a stripped-down `filename` for anything
    that cannot read it. Quotes and backslashes are removed rather than escaped, since
    neither belongs in a filename being offered to a client.
    """
    ascii_name = unicodedata.normalize("NFKD", filename).encode("ascii", "ignore").decode()
    ascii_name = ascii_name.replace('"', "").replace("\\", "") or "download"
    return f"attachment; filename=\"{ascii_name}\"; filename*=UTF-8''{quote(filename)}"


def noindex(response):
    """
    Mark a private response: keep it out of search indexes, and out of caches.

    The `noindex` half keeps the URL from being advertised without listing it in
    robots.txt. `private, no-store` is the half that matters for the photographs
    themselves — without it nothing stops a shared proxy, or a browser on a shared
    machine, from keeping a copy of a client's gallery long after it has expired and been
    deleted from disk.
    """
    response["X-Robots-Tag"] = "noindex, nofollow, noarchive"
    response["Cache-Control"] = "private, no-store"
    return response
