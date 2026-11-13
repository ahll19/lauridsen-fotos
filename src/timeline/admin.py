from django import forms
from django.contrib import admin, messages
from django.db import transaction
from django.db.models import Count
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin, TranslationTabularInline
from ordered_model.admin import OrderedInlineModelAdminMixin, OrderedTabularInline

from core.forms import MultipleImageField
from portfolio.admin import thumb

from .models import Tag, TimelineEntry, TimelineEntryPhoto


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
    list_display = ("title", "date", "photo_count", "tag_names", "visible")
    list_filter = ("visible", "tags")
    autocomplete_fields = ("tags",)
    list_editable = ("visible",)
    date_hierarchy = "date"
    prepopulated_fields = {"slug": ("title_da",)}

    @admin.display(description=_("photos"))
    def photo_count(self, obj):
        return obj.photos.count()

    @admin.display(description=_("tags"))
    def tag_names(self, obj):
        return ", ".join(obj.tag_list())

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

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


@admin.register(Tag)
class TagAdmin(TranslationAdmin):
    """
    The one list of tags. Entries pick from it; this is where it is tidied.

    Two spellings of the same idea are put right by merging them, which moves every entry
    onto one tag and deletes the other, rather than by editing entries one at a time.
    """

    list_display = ("name_da", "name_en", "entry_count")
    search_fields = ("name_da", "name_en")
    actions = ["merge_tags"]

    def get_queryset(self, request):
        return super().get_queryset(request).annotate(entry_total=Count("entries"))

    @admin.display(description=_("timeline entries"), ordering="entry_total")
    def entry_count(self, obj):
        return obj.entry_total

    @admin.action(description=_("Merge the selected tags into one"))
    def merge_tags(self, request, queryset):
        """Keeps the most used of the selected tags; ties go to the alphabetically first."""
        tags = sorted(queryset, key=lambda tag: (-tag.entry_total, tag.name_da.lower()))
        if len(tags) < 2:
            self.message_user(
                request, _("Select at least two tags to merge."), level=messages.WARNING
            )
            return
        kept, merged = tags[0], tags[1:]
        with transaction.atomic():
            for tag in merged:
                for entry in tag.entries.all():
                    entry.tags.add(kept)
                tag.delete()
        self.message_user(
            request,
            _("Merged %(names)s into “%(kept)s”. Rename it if another spelling is better.")
            % {"names": ", ".join(f"“{tag.name}”" for tag in merged), "kept": kept.name},
        )
