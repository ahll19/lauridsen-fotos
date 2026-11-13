from datetime import timedelta

from django import forms
from django.contrib import admin, messages
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from ordered_model.admin import OrderedTabularInline

from core.forms import MultipleImageField

from .models import ClientGallery, GalleryPhoto

EXTENSION_DAYS = 30


class GalleryPhotoInline(OrderedTabularInline):
    model = GalleryPhoto
    fields = ("image", "order", "move_up_down_links")
    readonly_fields = ("order", "move_up_down_links")
    extra = 0
    ordering = ("order",)


class ClientGalleryForm(forms.ModelForm):
    """Adds the bulk upload field and a one-off password override to the change form."""

    upload = MultipleImageField(
        required=False,
        label=_("Add photographs"),
        help_text=_("Select as many files as you like. They are appended to the gallery."),
    )
    new_password = forms.CharField(
        required=False,
        label=_("Set a specific password"),
        help_text=_("Leave empty to have one generated. Only ever shown once, right after saving."),
    )

    class Meta:
        model = ClientGallery
        fields = ["label", "client_name", "expires_at"]


@admin.register(ClientGallery)
class ClientGalleryAdmin(admin.ModelAdmin):
    form = ClientGalleryForm
    inlines = [GalleryPhotoInline]
    list_display = (
        "label",
        "status",
        "photo_count",
        "expires_at",
        "remaining",
        "zip_state",
        "link",
    )
    list_filter = ("deleted",)
    search_fields = ("label", "client_name", "slug")
    readonly_fields = ("slug", "created_at", "link", "zip_state")
    actions = [
        "action_rebuild_zip",
        "action_regenerate_password",
        "action_extend",
        "action_expire_now",
    ]

    fieldsets = (
        (None, {"fields": ("label", "client_name", "expires_at")}),
        (_("Access"), {"fields": ("slug", "link", "new_password")}),
        (_("Photographs"), {"fields": ("upload", "zip_state")}),
        (_("Record"), {"fields": ("created_at",), "classes": ("collapse",)}),
    )

    # --- Columns -------------------------------------------------------------

    @admin.display(description=_("status"))
    def status(self, obj):
        if obj.deleted:
            return _("Expired — photos deleted")
        if obj.is_expired:
            return _("Past expiry — awaiting cleanup")
        return _("Active")

    @admin.display(description=_("photos"))
    def photo_count(self, obj):
        return obj.photos.count()

    @admin.display(description=_("remaining"))
    def remaining(self, obj):
        if obj.deleted or obj.is_expired:
            return "—"
        return _("%(days)d days") % {"days": obj.days_remaining}

    @admin.display(description=_("ZIP"))
    def zip_state(self, obj):
        if not obj.pk or obj.deleted:
            return "—"
        if obj.zip_exists:
            # The file and the timestamp can disagree — a restore from backup brings one
            # back without the other, as does a crash between writing the archive and
            # saving the row. Reporting the file as present beats raising on the changelist.
            if not obj.zip_built_at:
                return _("Built (date unknown)")
            return _("Built %(when)s") % {"when": obj.zip_built_at.strftime("%Y-%m-%d %H:%M")}
        return format_html("<strong>{}</strong>", _("Not built — run “Rebuild download ZIP”"))

    @admin.display(description=_("client link"))
    def link(self, obj):
        if not obj.pk:
            return "—"
        url = obj.get_absolute_url()
        return format_html('<a href="{}" target="_blank">{}</a>', url, url)

    # --- Saving --------------------------------------------------------------

    def save_model(self, request, obj, form, change):
        """
        Generate the password on creation and show the plaintext exactly once.

        It is hashed on the way in and cannot be recovered afterwards, so this message is
        the only chance to copy it.
        """
        requested = form.cleaned_data.get("new_password")

        if not change or requested:
            plaintext = obj.set_password(requested or None)
            super().save_model(request, obj, form, change)
            self.message_user(
                request,
                format_html(
                    "{} <code style='font-size:1.1em'>{}</code> — {}",
                    _("Password for this gallery:"),
                    plaintext,
                    _("copy it now, it cannot be shown again."),
                ),
                level=messages.WARNING,
            )
        else:
            super().save_model(request, obj, form, change)

        uploads = form.cleaned_data.get("upload") or []
        for uploaded in uploads:
            GalleryPhoto.objects.create(gallery=obj, image=uploaded)
        if uploads:
            self.message_user(
                request,
                _(
                    "Added %(count)d photograph(s). Rebuild the download ZIP "
                    "before sharing the link."
                )
                % {"count": len(uploads)},
                level=messages.INFO,
            )

    def delete_queryset(self, request, queryset):
        """
        Delete the photographs too, when several galleries go at once.

        The admin's "Delete selected" runs `queryset.delete()`, which does not call each
        model's `delete()` — so the override there, and with it the removal of the files,
        was skipped for exactly the bulk case. The rows vanished and the client
        photographs stayed on disk indefinitely, which for expired client work is the one
        outcome `functional_design.md` §10 rules out.
        """
        for gallery in queryset:
            gallery.delete_files()
        super().delete_queryset(request, queryset)

    # --- Actions -------------------------------------------------------------

    @admin.action(description=_("Rebuild download ZIP"))
    def action_rebuild_zip(self, request, queryset):
        for gallery in queryset:
            if gallery.deleted:
                continue
            count = gallery.build_zip()
            if count:
                self.message_user(
                    request,
                    _("'%(label)s': archived %(count)d photograph(s).")
                    % {"label": gallery.label, "count": count},
                )
            else:
                self.message_user(
                    request,
                    _("'%(label)s' has no photographs to archive.") % {"label": gallery.label},
                    level=messages.WARNING,
                )

    @admin.action(description=_("Regenerate password"))
    def action_regenerate_password(self, request, queryset):
        for gallery in queryset:
            plaintext = gallery.set_password()
            gallery.save(update_fields=["password_hash"])
            self.message_user(
                request,
                format_html(
                    "{} <code style='font-size:1.1em'>{}</code>",
                    _("New password for '%(label)s':") % {"label": gallery.label},
                    plaintext,
                ),
                level=messages.WARNING,
            )

    @admin.action(description=_("Extend by 30 days"))
    def action_extend(self, request, queryset):
        for gallery in queryset.filter(deleted=False):
            gallery.expires_at = max(gallery.expires_at, timezone.now()) + timedelta(
                days=EXTENSION_DAYS
            )
            gallery.save(update_fields=["expires_at"])
        self.message_user(request, _("Extended by %(days)d days.") % {"days": EXTENSION_DAYS})

    @admin.action(description=_("Expire now (deletes the photographs)"))
    def action_expire_now(self, request, queryset):
        for gallery in queryset.filter(deleted=False):
            count = gallery.expire_now()
            self.message_user(
                request,
                _("'%(label)s': %(count)d photograph(s) deleted from disk.")
                % {"label": gallery.label, "count": count},
                level=messages.WARNING,
            )
