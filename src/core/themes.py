"""
Variations on Atelier, for choosing between (ROADMAP 0.2.0).

The direction is settled: Atelier. What is still open is which version of it. Each variation
below changes **one axis** and holds everything else constant, so a comparison actually tells
you something — if three things move at once, a preference is unattributable.

    Sage    accent hue        terracotta → deep sage
    Slate   temperature       warm paper → cool paper, deeper ink, indigo accent
    Press   typography        Fraunces → a high-contrast serif, at a larger scale

Each is a stylesheet layered over `site.css`, which holds the structure and the original
look. Overriding rather than replacing keeps the original exactly as it is — it is the
thing being compared against.

This is a decision-making tool, not a site feature. Once a version is chosen, the winner is
folded into `site.css`, the losers are deleted, and this module goes with them. It is off
wherever `DESIGN_PREVIEW_ENABLED` is false, so it never reaches visitors.
"""

from dataclasses import dataclass, field

FONTS = "https://fonts.googleapis.com/css2?{families}&display=swap"


@dataclass(frozen=True)
class Theme:
    slug: str
    name: str
    axis: str  # what this variation changes
    tagline: str
    description: str
    stylesheet: str | None  # relative to static/, None for the original
    fonts: str | None  # None when site.css's own font link already covers it
    swatches: tuple[str, ...] = field(default_factory=tuple)


THEMES = [
    Theme(
        slug="atelier",
        name="Atelier",
        axis="the original",
        tagline="Warm paper, terracotta, Fraunces",
        description=(
            "Unchanged. Warm off-white paper with every neutral hue-shifted toward brown, a "
            "single desaturated terracotta accent, and a soft serif against a neutral sans. "
            "This is the one already in use; the others move exactly one thing away from it."
        ),
        stylesheet=None,
        fonts=None,
        swatches=("#fbfaf8", "#f3f0eb", "#b4553a", "#1a1815"),
    ),
    Theme(
        slug="atelier-sage",
        name="Atelier Sage",
        axis="accent hue",
        tagline="Same paper and type, green accent",
        description=(
            "Identical to the original except the accent: terracotta becomes a deep, dusty "
            "sage. Green recedes where terracotta advances, so the accent stops drawing the "
            "eye and starts sitting quietly behind the photographs. Cooler and calmer — ask "
            "yourself whether it now reads as understated or as merely absent."
        ),
        stylesheet="css/themes/atelier-sage.css",
        fonts=None,
        swatches=("#fbfaf8", "#f3f0eb", "#5e7356", "#1a1815"),
    ),
    Theme(
        slug="atelier-slate",
        name="Atelier Slate",
        axis="temperature and contrast",
        tagline="Cooler paper, deeper ink, indigo accent",
        description=(
            "The same layout and type, moved from warm to cool: the yellow comes out of the "
            "paper, the ink goes deeper and slightly blue, and the accent becomes a muted "
            "indigo. Crisper and more gallery-like, less like a printed page. Cool paper "
            "flatters cool photographs — worth judging against your own winter and coastal "
            "work rather than the warm demo images."
        ),
        stylesheet="css/themes/atelier-slate.css",
        fonts=None,
        swatches=("#fafbfc", "#eef1f3", "#46597a", "#14171a"),
    ),
    Theme(
        slug="atelier-press",
        name="Atelier Press",
        axis="typography",
        tagline="Same colours, a sharper serif, bigger",
        description=(
            "Colours untouched — only the type changes. Fraunces, which is soft and a little "
            "quirky, is replaced by a high-contrast serif with fine hairlines, set larger "
            "and tighter. More editorial and more formal; the page feels art-directed rather "
            "than gentle. The trade is warmth for authority."
        ),
        stylesheet="css/themes/atelier-press.css",
        fonts=FONTS.format(families="family=Bodoni+Moda:opsz,wght@6..96,400;6..96,500"),
        swatches=("#fbfaf8", "#f3f0eb", "#b4553a", "#1a1815"),
    ),
]

BY_SLUG = {theme.slug: theme for theme in THEMES}
DEFAULT = THEMES[0]


def get(slug):
    """The named variation, falling back to the original for anything unrecognised."""
    return BY_SLUG.get(slug or "", DEFAULT)
