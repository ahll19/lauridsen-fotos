# Changelog

All notable changes to this project are recorded here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and the project uses
[Semantic Versioning](https://semver.org/).

Sections are generated from Conventional Commit subjects by `scripts/release.sh prepare`;
anything worth saying that a commit subject doesn't capture can be written under
`[Unreleased]` by hand and will be carried into the next release.

## [Unreleased]

The configuration production needs, checked on a laptop rather than discovered on a server.
Still local-only — 0.3.0 changes how the site is configured, not where it runs.

### Added

- `scripts/prodcheck.sh` runs the whole stack the way the VPS will and checks it: Django's
  deployment checklist, content-hashed static assets actually being served, every reachable
  page crawled for a 200, the error pages, and the mail relay's sender policy. It puts the
  development stack back afterwards, whatever the outcome.
- Custom 400, 403, 404 and 500 pages in Danish and English, styled like the rest of the
  site. Until now a mistyped address got Django's unstyled English paragraph. 403 and 500
  earn their place too: 403 is what a form left open too long produces, and it now says so
  instead of "forbidden".
- A real outbound mail relay. Postfix, delivering straight to recipients rather than
  through a sending service, refusing to send as any domain but its own, and publishing no
  ports — reachable only from inside the Docker network. The reasoning, and what it costs,
  is in [ADR 0004](docs/decisions/0004-deliver-mail-directly-rather-than-through-a-smarthost.md).
- `.env.example` now opens with what every reader of a committed example file should be
  told — that none of its values may be used on a server — and says how to generate each
  production secret.

### Changed

- Mailpit and Postfix are two compose services selected by `COMPOSE_PROFILES`, rather than
  one service with a swapped image. They share nothing but the protocol, and the shared
  `MAIL_RELAY_IMAGE` variable failed in the worst possible way: an `.env` still carrying
  the old value started Mailpit under the name `postfix` — a relay that accepts every
  message and delivers none of them, silently. The images are pinned per service now, so a
  stale value is inert instead of wrong. Both answer to `mail-relay` on the Docker network,
  so the application's `EMAIL_HOST` never changes.
- Whether the site is served over HTTPS is now its own setting rather than implied by
  `DJANGO_DEBUG`. The two are not the same question, and conflating them made the
  production configuration impossible to run locally: the SSL redirect sent every request
  to a port nothing listens on, and the session and CSRF cookies, marked Secure, were
  discarded by the browser — so the admin could not be logged into and no form could be
  submitted. It defaults to on whenever debug is off, and `check --deploy` still objects if
  it is off in production.
- `scripts/dev.sh up` removes containers left over from an older version of the compose
  file. Renaming a service otherwise leaves the old one running and holding its port.

### Fixed

- The Danish catalogue gained the thirteen strings the new error pages introduced, and a
  fuzzy match that had rendered "Browse the portfolio" as "Fra portfolioen".

## [0.2.0] - 2026-09-14

The site has a settled visual identity and has been taken apart and rebuilt from nothing to
check it. Still local-only: there is no server yet, and nothing here assumes one.

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
- Links that leave the site, and calls to action, open in a new tab: Instagram, Facebook,
  "skriv til mig" and the pricing enquiry button — which was taking away the prices the
  visitor was comparing. Browsing still moves the URL you are on; only actions cost a tab.
- The header no longer holds the top of a phone screen. It was sticky and two lines tall, so
  it kept that space through every scroll; below 760px it now scrolls away with the page and
  drops the tagline.
- `README.md` is an operating manual rather than an overview: running it, publishing, client
  galleries, configuration and code, with command tables kept as reference at the end.
- Ansible is now how the remote host will be managed, so the server is rebuilt from a clone
  rather than from memory: recorded in ADR 0002 and reflected in `architecture.md` §2, §10
  and §11, with `scripts/verify.sh` ready to lint the playbooks and refuse an unencrypted
  vault file. The `ansible/` directory itself is 0.4.0's work — this entry originally said
  it had been added, which it had not.

### Fixed

- The admin's section headings were in English — "Galleries", "Pages", "Portfolio",
  "Timeline". Django falls back to the raw app label when an app declares no verbose name,
  and none of the five did, so the one part of the admin the translation pass could not
  reach was the first thing you see on the index page.
- The pricing page's enquiry button did not say which package it was about. The link had
  carried the package name as a query parameter since it was written; the contact view never
  read it, so enquiries arrived with no indication of what prompted them.
- Right-click was not blocked on the largest public images. The deterrent was bound to each
  image at load, which missed the lightbox — it builds its own overlay outside the photo
  grid, showing the biggest derivative — and the portfolio index and category pages, which
  had never opted in. Still a speed bump rather than protection.
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
