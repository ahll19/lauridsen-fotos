"""
Gallery unlock state.

A correct password sets a signed, gallery-scoped cookie. The signature is what makes it
trustworthy — the cookie carries no secret of its own, so copying it to another gallery's
URL fails the scope check, and tampering fails the signature check.
"""

from django.conf import settings
from django.core import signing

SALT = "galleries.access"


def cookie_name(gallery):
    return f"gallery_{gallery.slug}"


def grant(response, gallery):
    """Mark this browser as having entered the correct password for one gallery."""
    response.set_cookie(
        cookie_name(gallery),
        signing.dumps({"slug": gallery.slug}, salt=SALT),
        max_age=settings.GALLERY_SESSION_MAX_AGE,
        httponly=True,
        samesite="Lax",
        secure=not settings.DEBUG,
        path=gallery.get_absolute_url(),
    )
    return response


def revoke(response, gallery):
    response.delete_cookie(cookie_name(gallery), path=gallery.get_absolute_url())
    return response


def has_access(request, gallery):
    raw = request.COOKIES.get(cookie_name(gallery))
    if not raw:
        return False
    try:
        payload = signing.loads(raw, salt=SALT, max_age=settings.GALLERY_SESSION_MAX_AGE)
    except signing.BadSignature:
        return False
    return payload.get("slug") == gallery.slug
