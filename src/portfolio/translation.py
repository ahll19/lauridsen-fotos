from modeltranslation.translator import TranslationOptions, register

from .models import Album, Category, Photo


@register(Category)
class CategoryTranslation(TranslationOptions):
    fields = ("name", "description")


@register(Album)
class AlbumTranslation(TranslationOptions):
    fields = ("name", "description")


@register(Photo)
class PhotoTranslation(TranslationOptions):
    fields = ("caption", "alt_text")
