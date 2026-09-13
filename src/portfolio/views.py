from django.shortcuts import get_object_or_404, render

from .models import Album, Category


def index(request):
    """Portfolio landing: the categories, each with its albums' cover images."""
    categories = Category.objects.visible().prefetch_related("albums").order_by("order")
    return render(request, "portfolio/index.html", {"categories": categories})


def category(request, slug):
    category_obj = get_object_or_404(Category.objects.visible(), slug=slug)
    albums = category_obj.visible_albums().prefetch_related("photos")
    return render(
        request,
        "portfolio/category.html",
        {"category": category_obj, "albums": albums},
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
        },
    )
