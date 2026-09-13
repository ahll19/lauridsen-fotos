from pathlib import Path

from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import translation
from django.utils.translation import gettext as _
from django.views.decorators.http import require_GET, require_http_methods

from .access import grant, has_access
from .models import ClientGallery, GalleryPhoto
from .serving import noindex, protected_file_response
from .thumbnails import private_thumbnail


def _get_gallery(slug):
    return get_object_or_404(ClientGallery, slug=slug)


def _honour_language_cookie(request):
    """
    Let a client read their gallery in either language.

    Gallery URLs deliberately carry no language prefix: the link handed to a client should
    be one fixed string, and a private page has no business existing at two addresses.
    That puts them outside `i18n_patterns`, where LocaleMiddleware pins the language to the
    site default — so the visitor's own choice has to be applied here instead.

    Prefixing these URLs would also break the unlock cookie, which is scoped to the
    gallery's path: unlocking at /en/g/<slug>/ would leave /g/<slug>/ locked again.
    """
    language = request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME)
    if language and translation.check_for_language(language):
        translation.activate(language)
        request.LANGUAGE_CODE = language


def _require_access(request, gallery):
    """Every private response re-checks the cookie; nothing trusts a previous page."""
    if not gallery.is_available or not has_access(request, gallery):
        raise Http404("Not available")


@require_http_methods(["GET", "HEAD", "POST"])
def detail(request, slug):
    """
    The gallery page.

    Never renders a photograph before a password has been accepted, and says nothing
    about why a password was rejected.
    """
    _honour_language_cookie(request)
    gallery = _get_gallery(slug)

    # Expired or already emptied: the URL keeps answering, but with an explanation
    # rather than the content or a bare 404.
    if not gallery.is_available:
        return noindex(
            render(request, "galleries/unavailable.html", {"gallery": gallery}, status=410)
        )

    if request.method == "POST":
        if gallery.check_gallery_password(request.POST.get("password", "")):
            return noindex(grant(redirect(gallery.get_absolute_url()), gallery))
        return noindex(
            render(
                request,
                "galleries/locked.html",
                {
                    "gallery": gallery,
                    "error": _("That password is not correct."),
                },
                status=401,
            )
        )

    if not has_access(request, gallery):
        return noindex(render(request, "galleries/locked.html", {"gallery": gallery}))

    photos = gallery.photos.all()
    return noindex(
        render(
            request,
            "galleries/detail.html",
            {
                "gallery": gallery,
                "photos": photos,
                "photo_count": len(photos),
            },
        )
    )


@require_GET
def photo(request, slug, photo_id):
    """A gallery photograph, as a web-sized derivative for on-page viewing."""
    gallery = _get_gallery(slug)
    _require_access(request, gallery)

    item = get_object_or_404(GalleryPhoto, pk=photo_id, gallery=gallery)
    alias = "lightbox" if request.GET.get("size") == "large" else "grid"
    thumb = private_thumbnail(item.image, alias)

    return noindex(protected_file_response(Path(thumb.path)))


@require_GET
def download_photo(request, slug, photo_id):
    """The untouched original, EXIF and all — this is the client's own photograph."""
    gallery = _get_gallery(slug)
    _require_access(request, gallery)

    item = get_object_or_404(GalleryPhoto, pk=photo_id, gallery=gallery)
    return noindex(
        protected_file_response(Path(item.image.path), filename=item.filename, as_attachment=True)
    )


@require_GET
def download_zip(request, slug):
    gallery = _get_gallery(slug)
    _require_access(request, gallery)

    if not gallery.zip_exists:
        # The owner has not run "Rebuild download ZIP" yet. Individual downloads still work.
        raise Http404("No archive built")

    return noindex(
        protected_file_response(
            gallery.zip_path,
            filename=f"{gallery.slug}.zip",
            content_type="application/zip",
            as_attachment=True,
        )
    )
