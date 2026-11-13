from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _

from core.meta import page_meta

from .models import Tag, TimelineEntry


def index(request):
    """Reverse-chronological feed; ordering comes from the model's Meta."""
    entries = TimelineEntry.objects.visible().prefetch_related("photos")

    tag = request.GET.get("tag", "").strip()
    if tag:
        entries = entries.filter(tags__name__iexact=tag)

    # Only tags some published entry carries, so no filter ever leads to an empty page.
    all_tags = list(
        Tag.objects.filter(entries__visible=True).distinct().values_list("name", flat=True)
    )

    return render(
        request,
        "timeline/index.html",
        {
            "entries": entries,
            "tags": all_tags,
            "active_tag": tag,
            **page_meta(request, title=_("Timeline")),
        },
    )


def entry(request, slug):
    entry_obj = get_object_or_404(TimelineEntry.objects.visible(), slug=slug)
    photos = entry_obj.photos.all()
    first = photos.first()
    return render(
        request,
        "timeline/entry.html",
        {
            "entry": entry_obj,
            "photos": photos,
            **page_meta(
                request,
                title=entry_obj.title,
                description=entry_obj.caption,
                image=first.image if first else None,
            ),
        },
    )
