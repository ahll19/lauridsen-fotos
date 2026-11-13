from django import template

from core.text import render_text

register = template.Library()


@register.filter(is_safe=True)
def rich(value):
    """Text from the admin with its links and line breaks. See core/text.py."""
    return render_text(value)
