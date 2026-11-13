"""
Links in text written in the admin.

The text fields are plain text, and stay plain text: no HTML is ever taken from them. Two
things are turned into links when a page is rendered:

- a bare address, `https://example.com/page` or `www.example.com`, which shows as written;
- `[the words to show](https://example.com/page)`, which shows the words.

A link target may be an http or https address, a `mailto:` address, or a path on this site
starting with `/`. Anything else in square brackets is left exactly as typed. Line breaks
become `<br>`, as `linebreaksbr` did before, so existing text renders as it always has.
"""

import re

from django.utils.html import format_html, urlize
from django.utils.safestring import mark_safe
from django.utils.translation import gettext_lazy as _

LINK = re.compile(
    r"\[(?P<label>[^\[\]\n]+)\]\((?P<url>https?://[^\s()]+|mailto:[^\s()]+|/[^\s()]*)\)"
)

# A bare address longer than this is shown shortened; the link still goes to all of it.
SHOWN_URL_LENGTH = 60


def render_text(value):
    """The text as HTML, with its links and line breaks."""
    text = str(value or "").replace("\r\n", "\n")
    parts, position = [], 0
    for match in LINK.finditer(text):
        parts.append(_bare(text[position : match.start()]))
        parts.append(format_html('<a href="{}">{}</a>', match["url"], match["label"]))
        position = match.end()
    parts.append(_bare(text[position:]))
    return mark_safe("".join(parts).replace("\n", "<br>"))


def plain_text(value):
    """The text with link syntax reduced to the words shown, for descriptions and previews."""
    return LINK.sub(lambda match: match["label"], str(value or ""))


def _bare(segment):
    # Escapes everything, then links any bare address. Never given the link syntax above.
    return urlize(segment, trim_url_limit=SHOWN_URL_LENGTH, nofollow=False, autoescape=True)


# Shown under each text field that supports links, in the admin.
LINK_HELP = _(
    "Web addresses become links by themselves. To make words a link, write "
    "[the words](https://address)."
)
