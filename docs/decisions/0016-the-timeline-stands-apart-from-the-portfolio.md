# 0016. The timeline stands apart from the portfolio

- **Date**: 2026-11-13
- **Status**: Accepted
- **Affects**: functional_design.md (Timeline); technical_design.md (data model, TimelineEntry)

## Context

functional_design.md lets a timeline entry "link back to a related Portfolio category".
In use, a category was made only so timeline entries could point to it. It had no albums,
so the portfolio showed it as an empty heading, and every entry linking to it sent visitors
to an empty page.

The timeline already has its own grouping: tags, chosen from a shared list
([ADR 0015](0015-links-in-text-and-a-shared-tag-list.md)).

## Decision

Timeline entries no longer link to a portfolio category. The field is removed, along with
the "Related … in the portfolio" line on the timeline. Categories group albums and nothing
else; the timeline is grouped by tags.

An entry that belongs with particular work can link to it in its text, which can point to
an album rather than only to a whole category.

Separately, a category is shown publicly only once it has at least one public album: on
the portfolio page, at its own address and in the sitemap. Ticking **Synlig** on an empty
category no longer puts an empty heading on the site.

## Consequences

The links existing entries had to a category are dropped when the field is removed, and
are not restored if the migration is reversed.

A category can be made visible before its first album is ready; it appears by itself when
that album is published.
