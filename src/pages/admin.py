from django.contrib import admin
from django.utils.translation import gettext_lazy as _
from modeltranslation.admin import TranslationAdmin
from ordered_model.admin import OrderedModelAdmin
from solo.admin import SingletonModelAdmin

from .models import (
    AboutSettings,
    ContactSettings,
    ContactSubmission,
    HomeSettings,
    PricingPackage,
    PricingSettings,
)


class TranslatedSingletonAdmin(TranslationAdmin, SingletonModelAdmin):
    """Singleton pages, with the Danish/English tabs modeltranslation adds."""


admin.site.register(HomeSettings, TranslatedSingletonAdmin)
admin.site.register(AboutSettings, TranslatedSingletonAdmin)
admin.site.register(ContactSettings, TranslatedSingletonAdmin)
admin.site.register(PricingSettings, TranslatedSingletonAdmin)


@admin.register(PricingPackage)
class PricingPackageAdmin(TranslationAdmin, OrderedModelAdmin):
    list_display = ("name", "price", "visible", "move_up_down_links")
    list_editable = ("visible",)


@admin.register(ContactSubmission)
class ContactSubmissionAdmin(admin.ModelAdmin):
    """Read-only: this is a record of what arrived, not something to edit after the fact."""

    list_display = ("submitted_at", "name", "email", "shoot_type", "preferred_date", "email_sent")
    list_filter = ("email_sent", "submitted_at")
    search_fields = ("name", "email", "message")
    readonly_fields = (
        "name",
        "email",
        "shoot_type",
        "preferred_date",
        "message",
        "submitted_at",
        "ip_address",
        "email_sent",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    @admin.display(description=_("delivered"), boolean=True)
    def delivered(self, obj):
        return obj.email_sent
