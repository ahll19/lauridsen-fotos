from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from easy_thumbnails.files import get_thumbnailer
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from ordered_model.admin import (
    OrderedInlineModelAdminMixin,
    OrderedModelAdmin,
    OrderedTabularInline,
)

from core.forms import MultipleFileField

from .models import Album, Category, Photo


def thumb(image, alias="admin"):
    if not image:
        return "—"
    try:
        return format_html(
            '<img src="{}" style="border-radius:4px" alt="">',
            get_thumbnailer(image)[alias].url,
        )
    except Exception:
        return "—"


@admin.register(Category)
class CategoryAdmin(TranslationAdmin, OrderedModelAdmin):
    list_display = ("name", "album_count", "visible", "move_up_down_links")
    list_editable = ("visible",)
    prepopulated_fields = {"slug": ("name_da",)}

    @admin.display(description=_("albums"))
    def album_count(self, obj):
        return obj.albums.count()


class PhotoInline(TranslationTabularInline, OrderedTabularInline):
    model = Photo
    fields = ("preview", "image", "caption", "order", "move_up_down_links")
    readonly_fields = ("preview", "order", "move_up_down_links")
    extra = 0
    ordering = ("order",)

    @admin.display(description=_("preview"))
    def preview(self, obj):
        return thumb(obj.image)


class AlbumForm(forms.ModelForm):
    upload = MultipleFileField(
        required=False,
        label=_("Add photographs"),
        help_text=_("Select several at once; they are appended in the order chosen."),
    )

    class Meta:
        model = Album
        fields = "__all__"


@admin.register(Album)
class AlbumAdmin(OrderedInlineModelAdminMixin, TranslationAdmin, OrderedModelAdmin):
    form = AlbumForm
    inlines = [PhotoInline]
    list_display = ("name", "category", "photo_count", "visible", "move_up_down_links")
    list_filter = ("category", "visible")
    list_editable = ("visible",)
    prepopulated_fields = {"slug": ("name_da",)}

    @admin.display(description=_("photos"))
    def photo_count(self, obj):
        return obj.photos.count()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        uploads = form.cleaned_data.get("upload") or []
        for uploaded in uploads:
            Photo.objects.create(album=obj, image=uploaded)
        if uploads:
            self.message_user(
                request,
                _("Added %(count)d photograph(s).") % {"count": len(uploads)},
                level=messages.INFO,
            )
