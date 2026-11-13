from modeltranslation.translator import TranslationOptions, register

from .models import Tag, TimelineEntry, TimelineEntryPhoto


@register(Tag)
class TagTranslation(TranslationOptions):
    fields = ("name",)


@register(TimelineEntry)
class TimelineEntryTranslation(TranslationOptions):
    fields = ("title", "caption")


@register(TimelineEntryPhoto)
class TimelineEntryPhotoTranslation(TranslationOptions):
    fields = ("caption", "alt_text")
