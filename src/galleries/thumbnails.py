"""
Derivatives for private photographs.

Public thumbnails go to the nginx-served cache directory. Gallery thumbnails must not —
anything under that path is world-readable by design. These are written alongside the
originals instead, inside the gallery's own directory, so they are only reachable through
the access-checked view and are removed by the same rmtree when the gallery expires.
"""

from django.conf import settings
from django.core.files.storage import FileSystemStorage
from easy_thumbnails.files import get_thumbnailer

private_storage = FileSystemStorage(location=settings.MEDIA_ROOT)

ALIASES = {
    "grid": {"size": (800, 800), "crop": False, "quality": 82},
    "lightbox": {"size": (1800, 1800), "crop": False, "quality": 85},
}


def private_thumbnail(image_field, alias="grid"):
    """Return the generated thumbnail file for a private image."""
    thumbnailer = get_thumbnailer(image_field)
    thumbnailer.thumbnail_storage = private_storage
    return thumbnailer.get_thumbnail(ALIASES[alias])
