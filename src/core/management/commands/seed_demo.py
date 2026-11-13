"""
Populate the site with demonstration content.

Generates its own placeholder imagery with Pillow rather than downloading anything, so it
works offline and ships no third-party photographs. Safe to re-run: it clears the demo
content it created first.
"""

import math
import random
from datetime import date, timedelta
from io import BytesIO

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from PIL import Image, ImageDraw, ImageFilter

from galleries.models import ClientGallery, GalleryPhoto
from pages.models import (
    AboutSettings,
    ContactSettings,
    HomeSettings,
    PricingPackage,
    PricingSettings,
)
from portfolio.models import Album, Category, Photo
from timeline.models import Tag, TimelineEntry, TimelineEntryPhoto

# Muted, photographic palettes — enough to read as images at thumbnail size.
PALETTES = [
    ((44, 52, 63), (188, 172, 148)),
    ((72, 61, 55), (214, 191, 162)),
    ((38, 48, 44), (168, 183, 160)),
    ((84, 58, 52), (226, 186, 160)),
    ((46, 44, 58), (178, 170, 190)),
    ((94, 76, 58), (232, 209, 175)),
]


def make_image(seed, width=1600, height=1100):
    """A soft, plausible-looking abstract image, deterministic for a given seed."""
    rng = random.Random(seed)
    top, bottom = rng.choice(PALETTES)

    image = Image.new("RGB", (width, height))
    draw = ImageDraw.Draw(image)

    for y in range(height):
        ratio = y / height
        draw.line(
            [(0, y), (width, y)],
            fill=tuple(int(top[i] + (bottom[i] - top[i]) * ratio) for i in range(3)),
        )

    # A few soft shapes so thumbnails aren't flat gradients.
    for _ in range(rng.randint(3, 6)):
        cx, cy = rng.randint(0, width), rng.randint(0, height)
        radius = rng.randint(width // 10, width // 3)
        shade = rng.randint(-30, 30)
        box = [cx - radius, cy - radius, cx + radius, cy + radius]
        draw.ellipse(
            box,
            fill=tuple(
                max(0, min(255, int(top[i] + (bottom[i] - top[i]) * 0.5) + shade)) for i in range(3)
            ),
        )

    image = image.filter(ImageFilter.GaussianBlur(radius=width // 22))

    # A horizon line gives the eye something to read as a photograph.
    horizon = int(height * (0.45 + 0.2 * math.sin(seed)))
    overlay = Image.new("RGB", (width, height - horizon), bottom)
    image.paste(Image.blend(image.crop((0, horizon, width, height)), overlay, 0.35), (0, horizon))

    buffer = BytesIO()
    image.save(buffer, format="JPEG", quality=88)
    return ContentFile(buffer.getvalue())


CATEGORIES = [
    {
        "slug": "bryllup",
        "da": ("Bryllup", "Hele dagen, fortalt som den var — ikke som den blev iscenesat."),
        "en": ("Weddings", "The whole day, told as it happened rather than as it was staged."),
        "albums": [
            (
                "sofie-og-jonas",
                ("Sofie & Jonas", "En junidag ved kysten."),
                ("Sofie & Jonas", "A June day by the coast."),
                8,
            ),
            (
                "mette-og-lars",
                ("Mette & Lars", "Sensommer i haven."),
                ("Mette & Lars", "Late summer in the garden."),
                6,
            ),
        ],
    },
    {
        "slug": "portraet",
        "da": ("Portræt", "Et ansigt, tid nok, og lys der ikke lyver."),
        "en": ("Portraits", "A face, enough time, and light that doesn't lie."),
        "albums": [
            (
                "studie",
                ("Studie", "Rent lys, ingen staffage."),
                ("Studio", "Clean light, no props."),
                6,
            ),
            (
                "udendoers",
                ("Udendørs", "Portrætter hvor folk bor og arbejder."),
                ("Outdoors", "Portraits where people live and work."),
                5,
            ),
        ],
    },
    {
        "slug": "erhverv",
        "da": ("Erhverv", "Billeder til dem der skal bruge dem til noget."),
        "en": ("Commercial", "Photographs for people who need them to do a job."),
        "albums": [
            ("vaerksted", ("Værksted", "Håndværk, tæt på."), ("Workshop", "Craft, up close."), 7),
        ],
    },
]

TIMELINE = [
    (
        "vinterlys-ved-vesterhavet",
        (
            "Vinterlys ved Vesterhavet",
            "Tre timer hvor lyset aldrig rigtig kom op, og det var hele pointen.",
        ),
        (
            "Winter light on the North Sea coast",
            "Three hours where the light never quite rose, which was the whole point.",
        ),
        "vinter, kyst, film",
        4,
        40,
    ),
    (
        "blaa-time-i-byen",
        ("Blå time i byen", "Den halve time hvor gadelys og himmel vejer lige meget."),
        ("Blue hour in the city", "The half hour where street light and sky weigh the same."),
        "by, aften",
        3,
        95,
    ),
    (
        "taage-i-skoven",
        ("Tåge i skoven", "Gik ud efter noget andet, kom hjem med det her."),
        ("Fog in the woods", "Went out looking for something else, came home with this."),
        "skov, tåge",
        4,
        160,
    ),
]

PACKAGES = [
    (
        (
            "Portræt",
            "Én times fotografering\n15 redigerede billeder\n"
            "Online galleri i 90 dage\nFuld brugsret",
            "2.500 kr.",
        ),
        (
            "Portrait",
            "One hour of photography\n15 edited photographs\n"
            "Online gallery for 90 days\nFull usage rights",
            "DKK 2,500",
        ),
    ),
    (
        (
            "Bryllup",
            "Op til 10 timers dækning\n400+ redigerede billeder\n"
            "Online galleri i 90 dage\nFuld brugsret\nForsamtale og lokationsbesøg",
            "14.000 kr.",
        ),
        (
            "Wedding",
            "Up to 10 hours of coverage\n400+ edited photographs\n"
            "Online gallery for 90 days\nFull usage rights\n"
            "Pre-shoot meeting and location visit",
            "DKK 14,000",
        ),
    ),
    (
        (
            "Erhverv",
            "Halv dag på lokation\n30 redigerede billeder\n"
            "Online galleri i 90 dage\nUdvidet kommerciel brugsret",
            "8.000 kr.",
        ),
        (
            "Commercial",
            "Half a day on location\n30 edited photographs\n"
            "Online gallery for 90 days\nExtended commercial usage rights",
            "DKK 8,000",
        ),
    ),
]


class Command(BaseCommand):
    help = "Fill the site with demonstration content, including a client gallery."

    def add_arguments(self, parser):
        parser.add_argument(
            "--gallery-password",
            default="demo-gallery-password",
            help="Password for the demo client gallery, so it can be opened without the admin.",
        )

    def handle(self, *args, **options):
        self.stdout.write("Clearing existing demo content…")
        Category.objects.all().delete()
        TimelineEntry.objects.all().delete()
        Tag.objects.all().delete()
        PricingPackage.objects.all().delete()
        ClientGallery.objects.all().delete()

        seed = 0

        # --- Portfolio -------------------------------------------------------
        for spec in CATEGORIES:
            category = Category.objects.create(
                slug=spec["slug"],
                name_da=spec["da"][0],
                name_en=spec["en"][0],
                description_da=spec["da"][1],
                description_en=spec["en"][1],
                visible=True,
            )
            for slug, da, en, count in spec["albums"]:
                album = Album.objects.create(
                    category=category,
                    slug=slug,
                    name_da=da[0],
                    name_en=en[0],
                    description_da=da[1],
                    description_en=en[1],
                    visible=True,
                )
                album.cover.save(f"{slug}-cover.jpg", make_image(seed), save=True)
                seed += 1
                for n in range(count):
                    photo = Photo(album=album)
                    photo.image.save(f"{slug}-{n + 1:02d}.jpg", make_image(seed), save=False)
                    photo.save()
                    seed += 1
            self.stdout.write(f"  {category.name_en}: {category.albums.count()} album(s)")

        # --- Timeline --------------------------------------------------------
        for slug, da, en, tags, count, days_ago in TIMELINE:
            entry = TimelineEntry.objects.create(
                slug=slug,
                title_da=da[0],
                title_en=en[0],
                caption_da=da[1],
                caption_en=en[1],
                date=date.today() - timedelta(days=days_ago),
                visible=True,
            )
            entry.tags.set(
                [
                    Tag.objects.get_or_create(name__iexact=name, defaults={"name": name})[0]
                    for name in (part.strip() for part in tags.split(","))
                    if name
                ]
            )
            for n in range(count):
                photo = TimelineEntryPhoto(entry=entry)
                photo.image.save(f"{slug}-{n + 1:02d}.jpg", make_image(seed), save=False)
                photo.save()
                seed += 1
        self.stdout.write(f"  Timeline: {TimelineEntry.objects.count()} entries")

        # --- Pricing ---------------------------------------------------------
        for da, en in PACKAGES:
            PricingPackage.objects.create(
                name_da=da[0],
                name_en=en[0],
                description_da=da[1],
                description_en=en[1],
                price_da=da[2],
                price_en=en[2],
                visible=True,
            )

        pricing = PricingSettings.get_solo()
        pricing.heading_da, pricing.heading_en = "Priser", "Pricing"
        pricing.intro_da = (
            "Faste pakker, så du ved hvad du får. Skal der noget andet til, så skriv."
        )
        pricing.intro_en = (
            "Fixed packages, so you know what you're getting. If you need something else, write."
        )
        pricing.faq_da = (
            "Skriv via kontaktformularen med dato og hvad det drejer sig om. "
            "Jeg vender tilbage inden for et par dage med et konkret tilbud. "
            "Halvdelen betales ved booking, resten når billederne leveres."
        )
        pricing.faq_en = (
            "Write through the contact form with a date and what it's about. "
            "I'll come back within a couple of days with a concrete offer. "
            "Half is paid at booking, the rest when the photographs are delivered."
        )
        pricing.save()

        # --- Singleton pages -------------------------------------------------
        home = HomeSettings.get_solo()
        home.business_name = "Lauridsen Fotos"
        home.tagline_da = "Fotografi fra Midtjylland"
        home.tagline_en = "Photography from central Jutland"
        home.intro_da = (
            "Jeg fotograferer bryllupper, portrætter og erhverv — helst med god tid og "
            "dagslys. Kig med i portfolioen, eller skriv og fortæl hvad du har brug for."
        )
        home.intro_en = (
            "I photograph weddings, portraits and commercial work — preferably with plenty "
            "of time and daylight. Have a look through the portfolio, or write and tell me "
            "what you need."
        )
        home.hero_image.save("hero.jpg", make_image(101, 2400, 1400), save=False)
        home.save()

        about = AboutSettings.get_solo()
        about.heading_da, about.heading_en = "Om mig", "About me"
        about.biography_da = (
            "Jeg har fotograferet i femten år, de sidste otte på fuld tid. Jeg arbejder "
            "hellere med det lys der er, end med det jeg selv slæber med."
        )
        about.biography_en = (
            "I've been photographing for fifteen years, the last eight full time. I'd "
            "rather work with the light that's there than the light I brought along."
        )
        about.how_i_work_da = (
            "Vi taler sammen først, så jeg ved hvad billederne skal bruges til. På dagen "
            "blander jeg mig så lidt som muligt. Du får billederne i et galleri inden for to uger."
        )
        about.how_i_work_en = (
            "We talk first, so I know what the photographs are for. On the day I stay out "
            "of the way as much as I can. You get the photographs in a gallery within two weeks."
        )
        about.portrait.save("portrait.jpg", make_image(202, 1200, 1500), save=False)
        about.save()

        contact = ContactSettings.get_solo()
        contact.heading_da, contact.heading_en = "Kontakt", "Contact"
        contact.intro_da = (
            "Skriv gerne med dato og hvad det drejer sig om, så vender jeg tilbage hurtigt."
        )
        contact.intro_en = (
            "Write with a date and what it's about, and I'll come back to you quickly."
        )
        contact.email = "hej@lauridsen-fotos.dk"
        contact.phone = "+45 12 34 56 78"
        contact.instagram_url = "https://instagram.com/"
        contact.save()

        # --- A client gallery ------------------------------------------------
        password = options["gallery_password"]
        gallery = ClientGallery(
            label="Sofie & Jonas — bryllup 14. juni",
            client_name="Sofie & Jonas",
            expires_at=timezone.now() + timedelta(days=90),
        )
        gallery.set_password(password)
        gallery.save()

        for n in range(9):
            photo = GalleryPhoto(gallery=gallery)
            photo.image.save(f"delivery-{n + 1:02d}.jpg", make_image(seed), save=False)
            photo.save()
            seed += 1

        gallery.build_zip()

        # An already-expired gallery, so the tombstone path is demonstrable too.
        expired = ClientGallery(
            label="Demo — udløbet galleri",
            client_name="Tidligere kunde",
            expires_at=timezone.now() - timedelta(days=2),
        )
        expired.set_password("does-not-matter")
        expired.save()
        expired.deleted = True
        expired.save(update_fields=["deleted"])

        self.stdout.write("")
        self.stdout.write(self.style.SUCCESS("Demo content created."))
        self.stdout.write("")
        self.stdout.write(f"  Client gallery : /g/{gallery.slug}/")
        self.stdout.write(f"  Password       : {password}")
        self.stdout.write(f"  Expired gallery: /g/{expired.slug}/")
