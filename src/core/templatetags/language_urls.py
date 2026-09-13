"""
Language switching that survives `prefix_default_language=False`.

`django.views.i18n.set_language` translates its `next` URL itself, but it can only do so
when the active language matches that URL's prefix — `translate_url` resolves the path
against the URL patterns of whichever language is active. That view lives outside
`i18n_patterns`, so `LocaleMiddleware` forces it to the default language (Danish). It can
therefore resolve `/portfolio/` but never `/en/portfolio/`, which made switching *away*
from English a silent no-op.

Computing the target here fixes that: a page is rendered with its own language active, so
the current URL always resolves, and `set_language` receives a `next` that is already
correct and leaves it alone.
"""

from django import template
from django.urls import translate_url

register = template.Library()


@register.simple_tag(takes_context=True)
def switch_language_url(context, language_code):
    """The current page's URL in another language, or the current URL if it has none."""
    request = context.get("request")
    if request is None:
        return "/"
    return translate_url(request.get_full_path(), language_code)
