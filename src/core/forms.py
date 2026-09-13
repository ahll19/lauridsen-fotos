"""Shared form pieces."""

from django import forms


class MultipleFileInput(forms.ClearableFileInput):
    allow_multiple_selected = True


class MultipleFileField(forms.FileField):
    """
    A file field accepting several files at once.

    Django's FileField deliberately handles one file, so multi-select needs this small
    wrapper. It is the whole of the "bulk upload" soft requirement — a native multiple
    <input type="file">, no JavaScript uploader.
    """

    def __init__(self, *args, **kwargs):
        kwargs.setdefault("widget", MultipleFileInput(attrs={"multiple": True}))
        super().__init__(*args, **kwargs)

    def clean(self, data, initial=None):
        single = super().clean
        if isinstance(data, (list, tuple)):
            return [single(item, initial) for item in data]
        return [single(data, initial)]
