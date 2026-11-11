from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _

from core.meta import page_meta

from .models import TimelineEntry


def index(request):
    """Reverse-chronological feed; ordering comes from the model's Meta."""
    entries = TimelineEntry.objects.visible().prefetch_related("photos")

    tag = request.GET.get("tag", "").strip()
    if tag:
        entries = entries.filter(tags__icontains=tag)

    all_tags = sorted({t for entry in TimelineEntry.objects.visible() for t in entry.tag_list()})

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
