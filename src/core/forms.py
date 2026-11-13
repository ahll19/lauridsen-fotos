"""Shared form pieces."""

from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleImageField(forms.ImageField):
    """
    An image field accepting several files at once.

    Django's ImageField deliberately handles one file, so multi-select needs this small
    wrapper. It is the whole of the "bulk upload" soft requirement — a native multiple
    <input type="file">, no JavaScript uploader.

    Every file is opened with Pillow before anything is saved. A PDF or an iPhone HEIC
    used to be stored as a photograph and shown on the site as an empty frame; now the
    whole save is refused and the message names each file that is not a usable image.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"multiple": True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        files = list(data) if isinstance(data, (list, tuple)) else [data]
        single = super().clean
        cleaned, rejected = [], []
        for item in files:
            try:
                cleaned.append(single(item, initial))
            except ValidationError:
                rejected.append(getattr(item, "name", "?"))
        if rejected:
            raise ValidationError(
                _(
                    "Not saved. These files are not images this site can show: %(names)s. "
                    "Export them as JPEG and try again."
                ),
                code="invalid_image",
                params={"names": ", ".join(rejected)},
            )
        return [item for item in cleaned if item]
