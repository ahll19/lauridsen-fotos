# 0003. Visual direction: Atelier Sage

- **Date**: 2026-09-13
- **Status**: Accepted
- **Affects**: closes the open item in `technical_design.md`, "Exact visual design (colors,
  type pairing, the 'one deliberate accent')"

## Context

`functional_design.md` §1 asks for a site that is "modern, minimalist, but not sterile —
restrained color palette and generous whitespace, punctuated by one deliberate accent". Both
design documents deliberately left the specifics open, calling it a design task rather than an
architectural one.

Rather than argue about it in the abstract, four complete directions were built and made
switchable on the running site, so they could be judged against real photographs and real
Danish text instead of mockups: the original warm direction (Atelier), a dark gallery-wall
treatment (Darkroom), a high-contrast printed one (Broadsheet), and a cool, soft one (Nordic).
Atelier was chosen.

A second round then varied Atelier itself along one axis at a time — accent hue (Sage),
temperature and contrast (Slate), and typography (Press) — so that a preference could be
attributed to a single change rather than to three at once.

## Decision

**Atelier Sage.** Warm off-white paper with every neutral hue-shifted toward brown so the page
reads as paper rather than screen; Fraunces as a display serif against Inter for body text;
and a single low-saturation sage accent, `#5e7356`.

The accent is the point of the whole exercise. Sage recedes where the original terracotta
advanced, so the accent stops pulling the eye away from the photographs — which is what an
accent on a photography site should do.

Errors do **not** use the accent. With a green accent, an accent-coloured error message would
sit beside a green success message and stop functioning as a signal, and red-for-error is too
strong a convention to override. Errors get their own token, `--alert: #a8443d` — the
terracotta the accent used to be, kept on for the one job it is still better at.

## Consequences

The palette now has two semantic colours rather than one. That is slightly more to hold in
mind, but it means error and success states can never be confused, which a single-accent
system could not guarantee once the accent went green.

The preview machinery — the theme switcher, the comparison page at `/design/`, the candidate
stylesheets, and the `DESIGN_PREVIEW_ENABLED` setting — has been deleted, as planned when it
was built. The rejected directions remain in git history and can be recovered if this decision
is ever revisited.

Because the whole palette lives in CSS custom properties on `:root`, changing the accent again
later means editing two values. Nothing else in the stylesheet hard-codes an accent-derived
colour.
