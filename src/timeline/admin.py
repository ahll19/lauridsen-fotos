from django import forms
from django.contrib import admin, messages
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from ordered_model.admin import OrderedInlineModelAdminMixin, OrderedTabularInline

from core.forms import MultipleImageField
from portfolio.admin import thumb

from .models import TimelineEntry, TimelineEntryPhoto


class TimelinePhotoInline(TranslationTabularInline, OrderedTabularInline):
    model = TimelineEntryPhoto
    fields = ("preview", "image", "caption", "alt_text", "order", "move_up_down_links")
    readonly_fields = ("preview", "order", "move_up_down_links")
    extra = 0
    ordering = ("order",)

    @admin.display(description=_("preview"))
    def preview(self, obj):
        return thumb(obj.image)


class TimelineEntryForm(forms.ModelForm):
    upload = MultipleImageField(required=False, label=_("Add photographs"))

    class Meta:
        model = TimelineEntry
        fields = "__all__"


@admin.register(TimelineEntry)
class TimelineEntryAdmin(OrderedInlineModelAdminMixin, TranslationAdmin):
    form = TimelineEntryForm
    inlines = [TimelinePhotoInline]
    list_display = ("title", "date", "photo_count", "tags", "visible")
    list_filter = ("visible", "related_category")
    list_editable = ("visible",)
    date_hierarchy = "date"
    prepopulated_fields = {"slug": ("title_da",)}

    @admin.display(description=_("photos"))
    def photo_count(self, obj):
        return obj.photos.count()

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        uploads = form.cleaned_data.get("upload") or []
        for uploaded in uploads:
            TimelineEntryPhoto.objects.create(entry=obj, image=uploaded)
        if uploads:
            self.message_user(
                request,
                _("Added %(count)d photograph(s).") % {"count": len(uploads)},
                level=messages.INFO,
            )
