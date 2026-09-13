"""
Visual directions, for choosing between (ROADMAP 0.2.0).

Each direction is a stylesheet layered over `site.css`, which holds the structure and the
default look. Overriding rather than replacing means the baseline direction stays exactly
as it is — it is the one already in use and the one being compared against.

This is a decision-making tool, not a site feature. Once a direction is chosen, the winner
is folded into `site.css`, the losers are deleted, and this module goes with them. It is
switched off wherever `DESIGN_PREVIEW_ENABLED` is false, so it never reaches visitors.
"""

from dataclasses import dataclass

FONTS = "https://fonts.googleapis.com/css2?{families}&display=swap"


@dataclass(frozen=True)
class Theme:
    slug: str
    name: str
    tagline: str
    description: str
    stylesheet: str | None  # relative to static/, None for the baseline
    fonts: str | None  # None means site.css's own font link is enough


THEMES = [
    Theme(
        slug="atelier",
        name="Atelier",
        tagline="Warm, editorial, quiet",
        description=(
            "The current direction. Warm off-white paper, a single terracotta accent, and a "
            "high-contrast serif against a plain sans. Restrained without being cold — the "
            "photographs supply the colour."
        ),
        stylesheet=None,
        fonts=None,
    ),
    Theme(
        slug="darkroom",
        name="Darkroom",
        tagline="Dark, gallery wall, photographs first",
        description=(
            "Near-black throughout, so images glow rather than sit on a page. All chrome is "
            "small, uppercase and widely tracked; there is no accent colour beyond a dim "
            "amber on interaction. Tight grid gaps and square corners make the photographs "
            "read as one continuous wall. The conventional choice for photographers, for a "
            "reason — but it commits hard, and thin type on black needs good photographs to "
            "carry it."
        ),
        stylesheet="css/themes/darkroom.css",
        fonts=FONTS.format(
            families="family=Archivo:wght@300;400;500&family=Archivo+Narrow:wght@400;500"
        ),
    ),
    Theme(
        slug="broadsheet",
        name="Broadsheet",
        tagline="Printed, high contrast, hairline rules",
        description=(
            "Black ink on white, built like a photo book: a large serif headline, hairline "
            "rules separating sections, italic captions, and asymmetric margins. Buttons are "
            "underlined text rather than boxes. Feels considered and slightly formal — good "
            "for weddings, arguably too serious for commercial work."
        ),
        stylesheet="css/themes/broadsheet.css",
        fonts=FONTS.format(
            families="family=Instrument+Serif:ital@0;1&family=Inter:wght@300;400;500"
        ),
    ),
    Theme(
        slug="nordic",
        name="Nordic",
        tagline="Cool, soft, airy",
        description=(
            "Pale cool greys with a muted sage accent, a geometric sans at light weights, "
            "generous line height, soft rounded corners and wide gaps. Calm and modern "
            "rather than dramatic. The friendliest of the four, and the easiest to read at "
            "length — but the least distinctive."
        ),
        stylesheet="css/themes/nordic.css",
        fonts=FONTS.format(families="family=DM+Sans:opsz,wght@9..40,300;9..40,500"),
    ),
]

BY_SLUG = {theme.slug: theme for theme in THEMES}
DEFAULT = THEMES[0]


def get(slug):
    """The named theme, falling back to the baseline for anything unrecognised."""
    return BY_SLUG.get(slug or "", DEFAULT)
