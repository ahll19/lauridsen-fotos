from modeltranslation.translator import TranslationOptions, register

from .models import AboutSettings, ContactSettings, HomeSettings, PricingPackage, PricingSettings


@register(HomeSettings)
class HomeSettingsTranslation(TranslationOptions):
    fields = ("tagline", "intro")


@register(AboutSettings)
class AboutSettingsTranslation(TranslationOptions):
    fields = ("heading", "biography", "how_i_work")


@register(ContactSettings)
class ContactSettingsTranslation(TranslationOptions):
    fields = ("heading", "intro")


@register(PricingSettings)
class PricingSettingsTranslation(TranslationOptions):
    fields = ("heading", "intro", "faq")


@register(PricingPackage)
class PricingPackageTranslation(TranslationOptions):
    fields = ("name", "description", "price")
