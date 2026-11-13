# 0015. Links in admin text, and timeline tags from a shared list

- **Date**: 2026-11-13
- **Status**: Accepted
- **Affects**: technical_design.md (data model, TimelineEntry)

## Context

Text written in the admin, such as album descriptions and the About page, was plain text
with line breaks. The first real album description pointed visitors to an exhibition and an
artist's Instagram, and the addresses showed as text that could not be clicked.

Timeline tags were a comma-separated text field on each entry. Over years of entries the
same subject gets spelled several ways, and the filter matched text inside other tags:
`hav` also found entries tagged `havn`.

## Decision

**Links.** Text fields stay plain text, and no HTML is ever taken from them. When a page is
rendered, a bare web address becomes a link, and `[words](https://address)` makes the words
a link. Targets may be http(s), `mailto:` or a path on this site. This is done by one
template filter (`core/text.py`); there is no editor, no Markdown library and no JavaScript.

A full Markdown or WYSIWYG editor was not chosen. It would bring a dependency, invite
formatting the site's design does not have, and mean sanitising HTML.

**Tags.** A `Tag` model holds one shared list, and entries choose from it in the admin with
the autocomplete Django ships. Names differing only in case are the same tag. The list has a
merge action for tidying up. Filtering matches a whole tag, not part of one. The existing
text was converted by a data migration, which can be reversed.

## Consequences

Existing text renders as before, except that addresses in it are now links.

Tags are the same in both languages, as they were before.

Square brackets followed by a parenthesised address are always read as a link. Text that
needs to show that literally cannot.
