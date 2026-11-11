from django.db.models import Prefetch
from django.shortcuts import get_object_or_404, render
from django.utils.translation import gettext as _

from core.meta import page_meta

from .models import Album, Category


def index(request):
    """Portfolio landing: the categories, each with its albums' cover images."""
    categories = (
        Category.objects.visible()
        # Prefetched into an attribute the template reads directly. Prefetching "albums"
        # and then calling category.visible_albums in the template threw the prefetch away
        # — that is a fresh query — and cost two more per category on top.
        .prefetch_related(
            Prefetch(
                "albums",
                queryset=Album.objects.visible().prefetch_related("photos"),
                to_attr="published_albums",
            )
        )
        .order_by("order")
    )
    return render(
        request,
        "portfolio/index.html",
        {"categories": categories, **page_meta(request, title=_("Portfolio"))},
    )


def category(request, slug):
    category_obj = get_object_or_404(Category.objects.visible(), slug=slug)
    albums = category_obj.visible_albums().prefetch_related("photos")
    return render(
        request,
        "portfolio/category.html",
        {
            "category": category_obj,
            "albums": albums,
            **page_meta(
                request,
                title=category_obj.name,
                description=category_obj.description,
                image=albums[0].cover_image if albums else None,
            ),
        },
    )


def album(request, category_slug, slug):
    category_obj = get_object_or_404(Category.objects.visible(), slug=category_slug)
    album_obj = get_object_or_404(Album.objects.visible(), category=category_obj, slug=slug)
    return render(
        request,
        "portfolio/album.html",
        {
            "category": category_obj,
            "album": album_obj,
            "photos": album_obj.photos.all(),
            **page_meta(
                request,
                title=album_obj.name,
                description=album_obj.description or category_obj.description,
                image=album_obj.cover_image,
            ),
        },
    )
