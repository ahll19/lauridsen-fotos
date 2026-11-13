from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _

from core.meta import page_meta

from .models import Tag, TimelineEntry


def index(request):
    """Reverse-chronological feed; ordering comes from the model's Meta."""
    entries = TimelineEntry.objects.visible().prefetch_related("photos")

    # A tag is named in the URL as shown, in either language, so a filtered link still
    # works after switching language. The active tag is then shown in the page's language.
    tag = request.GET.get("tag", "").strip()
    if tag:
        chosen = Tag.find(tag)
        entries = entries.filter(tags=chosen) if chosen else entries.none()
        tag = str(chosen) if chosen else tag

    # Only tags some published entry carries, so no filter ever leads to an empty page.
    all_tags = sorted(
        (str(t) for t in Tag.objects.filter(entries__visible=True).distinct()),
        key=str.lower,
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
