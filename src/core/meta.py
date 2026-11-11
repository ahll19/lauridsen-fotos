"""
What a page says about itself to search engines and link previews.

A link to an album pasted into a message is how most people will first meet this site, and
without these tags it arrives as a bare URL with no picture. Views call `page_meta` and
spread the result into their context; `templates/_social.html` renders it. Pages that must
say nothing about themselves — client galleries, error pages — override the `meta` block
and so never include that template at all.
"""

from django.utils.text import Truncator
from easy_thumbnails.exceptions import EasyThumbnailsError
from easy_thumbnails.files import get_thumbnailer

# Search engines cut a description at roughly this length.
DESCRIPTION_LENGTH = 160
# The `cover` derivative is 1200x800, close to the 1.91:1 shape link previews crop to.
PREVIEW_ALIAS = "cover"


def _preview_url(request, image):
    if not image:
        return ""
    try:
        return request.build_absolute_uri(get_thumbnailer(image)[PREVIEW_ALIAS].url)
    except (EasyThumbnailsError, OSError, ValueError):
        # A missing file must cost the preview image, not the page.
        return ""


def page_meta(request, title="", description="", image=None):
    """
    Context for the description and link-preview tags.

    Anything left empty falls back to the site-wide values in the template, so a page with
    no description of its own still gets the site's.
    """
    description = " ".join(str(description or "").split())
    if not image:
        # A page with no photograph of its own previews with the front page's.
        from pages.models import HomeSettings

        image = HomeSettings.get_solo().hero_image
    return {
        "meta_title": title,
        "meta_description": Truncator(description).chars(DESCRIPTION_LENGTH),
        "meta_image": _preview_url(request, image),
    }
