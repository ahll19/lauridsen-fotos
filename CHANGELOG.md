# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

Sections are generated from Conventional Commit subjects by `scripts/release.sh prepare`;
anything worth saying that a commit subject doesn't capture can be written under
`[Unreleased]` by hand and will be carried into the next release.

## [Unreleased]

### Added

- The full application, running locally on Docker Compose: nginx, gunicorn + Django, a cron
  container for scheduled jobs, and Mailpit standing in for the mail relay. No certbot yet —
  there is no domain to point it at.
- Portfolio (categories → albums → photos), timeline, pricing, contact, and about pages, all
  editable from the Django admin in Danish and English.
- Private client galleries: unguessable URL plus password, files served via X-Accel-Redirect
  after an access check, full-album ZIP, automatic deletion on expiry, and a tombstone page
  so a late client sees an explanation rather than a 404.
- `scripts/dev.sh` for running the stack, and `seed_demo` for a site full of demonstration
  content including a working client gallery.
- Test suite covering the gallery access rules, expiry, and the contact form.
- `ROADMAP.md`: milestones to 1.0.0, each with a definition of done.
- The visual direction is settled: **Atelier Sage** (ROADMAP 0.2.0, ADR 0003). Warm
  off-white paper, Fraunces against Inter, and a single low-saturation sage accent that
  recedes behind the photographs instead of competing with them. Chosen by building four
  complete directions and making them switchable on the running site, then varying the
  winner one axis at a time. The preview machinery that made that possible has been
  removed, as planned.

### Changed

- Error states no longer borrow the accent colour. With a green accent, an accent-coloured
  error would sit beside a green success message and stop reading as a warning, so errors
  get their own token — the terracotta the accent used to be.
- Ansible is now the way the remote host is managed: an `ansible/` directory with the
  environment and playbooks for provisioning, deployment, updates and backup/restore, so the
  server is rebuilt from a clone rather than from memory. Recorded in ADR 0002 and reflected
  in `architecture.md` §2, §10 and §11; `scripts/verify.sh` already lints it and refuses an
  unencrypted vault file.

### Fixed

- **The test suite wrote into the live data directory** and ran `rmtree` against it. Tests
  create galleries and then exercise expiry, so the deletion path was pointed at the same
  tree that holds real client photographs, separated only by slugs not colliding. Tests now
  get a temporary `DATA_ROOT`.
- **The contact form's rate limit was global rather than per visitor.** Behind nginx every
  request arrives from the proxy's address, so `5/h` meant five messages per hour from the
  whole internet — one sender could close the site's only enquiry route for everyone.
- **The visitor address recorded against a submission was chosen by the visitor**, taken from
  the left-most `X-Forwarded-For` entry, which is whatever the caller sent. It is now read
  from the trusted end of the chain.
- **Deleting client galleries in bulk left the photographs on disk.** The admin's "Delete
  selected" runs a queryset delete, which skips the model's own `delete()` — so the one path
  that removes the files was the one path that never ran.
- The Danish translation catalogue was missing 123 strings, so the whole admin rendered in
  English, and 19 more were marked fuzzy with wrong guesses (`client gallery` had become
  "Åbn galleri"). Catalogue regenerated, everything translated, plural of "album" corrected.
- A multi-line `{# … #}` in `base.html` was not a comment — Django's is single-line — so the
  text rendered into the navigation of every page.
- nginx marked unhashed static assets `immutable` for 30 days, so browsers would not re-fetch
  an edited stylesheet for a month. The policy is now `STATIC_CACHE_CONTROL`.
- `scripts/dev.sh` aborted with exit 127: it sources `.env`, where unquoted cron expressions
  ran as commands. `dev.sh up` started the stack and then died before reporting anything.
- `proxy_set_header Host $host` dropped the port, so every absolute URL the application built
  pointed at a port nothing listens on.
- Private gallery pages and downloads now send `Cache-Control: private, no-store`; the
  password form is rate limited; the ZIP is named for the gallery rather than its URL key;
  and non-ASCII download filenames are RFC 6266 encoded.
- The sitemap advertised `example.com`, omitted every English page, and listed albums inside
  unpublished categories — publishing the name and URL of work still being prepared.
- Error emails were sent while developing, the portfolio index discarded its own prefetch,
  and the gallery changelist could raise on a gallery whose ZIP file and timestamp disagree.
- The language toggle only worked one way. Switching to English worked; switching back to
  Danish set the cookie but left the visitor on the `/en/` URL, which decides the language,
  so nothing appeared to happen.
- Client galleries are now readable in both languages. Their URLs deliberately carry no
  language prefix, which had put them outside Django's language routing and pinned them to
  Danish.

## [0.1.0] - 2026-09-12

### Added

- Functional, architecture and technical design documents describing the whole setup.
- Project working rules in `CLAUDE.md`, workflow scripts in `scripts/`, and version-controlled
  git hooks enforcing branch protection and commit conventions locally.
