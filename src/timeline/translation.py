from modeltranslation.translator import TranslationOptions, register

from .models import TimelineEntry, TimelineEntryPhoto


@register(TimelineEntry)
class TimelineEntryTranslation(TranslationOptions):
    fields = ("title", "caption")


@register(TimelineEntryPhoto)
class TimelineEntryPhotoTranslation(TranslationOptions):
    fields = ("caption", "alt_text")
