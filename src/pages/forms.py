from django import forms
from django.utils.translation import gettext_lazy as _

from .models import ContactSubmission


class ContactForm(forms.ModelForm):
    """
    The contact form, with a honeypot.

    `website` is hidden from people by CSS and left empty by them; bots fill in every
    field they find. A non-empty value is rejected silently — telling a bot why would just
    help it try again.
    """

    website = forms.CharField(required=False, widget=forms.HiddenInput, label="")

    class Meta:
        model = ContactSubmission
        fields = ["name", "email", "shoot_type", "preferred_date", "message"]
        widgets = {
            "name": forms.TextInput(attrs={"autocomplete": "name"}),
            "email": forms.EmailInput(attrs={"autocomplete": "email"}),
            "shoot_type": forms.TextInput(attrs={"placeholder": _("Wedding, portrait, event…")}),
            "preferred_date": forms.DateInput(attrs={"type": "date"}),
            "message": forms.Textarea(attrs={"rows": 6}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["shoot_type"].required = False
        self.fields["preferred_date"].required = False
        for name, field in self.fields.items():
            if name != "website":
                field.widget.attrs.setdefault("class", "field__input")

    @property
    def is_bot(self):
        return bool(self.data.get("website"))
