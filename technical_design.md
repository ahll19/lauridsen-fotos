# Technical Design — Lauridsen Fotos Photography Portfolio

`functional_design.md` describes **what** the site does. This document is the technical
response to it — **how** each requirement gets implemented. For how the hosting environment
itself is built and operated (server, network, containers, backups, monitoring), see
`architecture.md`; this document assumes that environment and focuses on the application
running inside it.

## Technology stack

- **Language / framework**: Python 3.12, Django 5.x (current LTS at time of writing). Django
  is chosen specifically because its built-in admin site generates nearly the entire admin
  dashboard (functional design §9) directly from the data model, which removes almost all
  custom frontend/admin-UI work — a good fit given the team's backend-first background.
- **Web server**: gunicorn (application) behind nginx (reverse proxy, static/media serving) —
  see `architecture.md` §4.
- **Database**: SQLite, as a single file on the shared `/data` volume — appropriate for a
  single-admin, low-concurrency, low-traffic site; avoids running/backing up a separate
  database server for no real benefit at this scale.
- **Image handling**: Pillow for processing; `easy-thumbnails` generates and caches
  web-sized/derivative images on demand, so originals are never served publicly. Because
  Pillow re-encodes the image to produce each derivative, EXIF metadata — including GPS
  location tags — is stripped from every derivative by default; this is treated as a
  deliberate privacy decision (a public portfolio photo should never leak where it was
  taken), not an incidental side effect. Original files keep their full EXIF data intact,
  since those are either downloaded only by the client they belong to, or never served to
  the public at all.
- **Static vs. media files**: Django's own static assets (admin CSS/JS, the site's
  hand-written CSS/JS) are collected via `collectstatic` at image-build time into a path
  baked into the `app` image, and served by nginx directly from there. This is entirely
  separate from the `/data` media volume in `architecture.md`, which holds only
  user-uploaded content (photos, the database) — static assets ship with the code and are
  never written to at runtime.
- **Bilingual content (DA/EN)**: `django-modeltranslation`, which adds parallel language
  fields to models and surfaces them as language tabs directly in the Django admin forms —
  editing both languages is just filling in two columns on the same screen, no separate
  translation-file workflow for content. Static UI strings (button labels, nav, etc.) use
  Django's own built-in i18n framework (message catalogs).
- **Ordering**: `django-ordered-model` for drag-and-drop reordering of albums/photos in the
  admin (functional design §9 soft requirement).
- **Singleton content** (Home hero/tagline, About bio, Contact static info): `django-solo`,
  which gives a single editable "settings object" in the admin instead of an add/delete-able
  list — a good fit for content that only ever has one instance.
- **Auth**: Django's built-in `django.contrib.auth` for the single admin user. Client-gallery
  access is a separate, purpose-built mechanism (§8 below) — not a user-account system.
- **Email**: Django's SMTP email backend, pointed at the mail-relay container from
  `architecture.md`. This same channel carries both contact-form notifications and Django's
  built-in admin error-emails (see `architecture.md` §9), so no separate error-tracking
  service is needed to start.
- **Spam protection**: a honeypot field plus `django-ratelimit` as the baseline (cheap,
  no external dependency), capping contact-form submissions to 5 per IP address per hour;
  *(on the live server every visitor shares one address — see
  [ADR 0014](docs/decisions/0014-the-application-cannot-see-visitors-addresses.md))*
  Cloudflare Turnstile is a documented drop-in upgrade if spam becomes a real problem later
  — deliberately not built in from day one, per "keep it simple until proven necessary."
- **Frontend**: server-rendered Django templates, hand-written CSS (no build step, no
  Node dependency), and small amounts of vanilla JavaScript only where genuinely needed
  (lightbox navigation, disabling right-click/drag-save on gallery images, language-toggle
  persistence). This deliberately avoids introducing a JS build pipeline or framework, since
  it isn't needed for a content-led site and keeps the whole stack in Python end to end.

## Data model (sketch)

Key models and the fields that matter for the behavior described below (not an exhaustive
schema):

- **Category** — `name` (DA/EN), `slug`, `order`, `visible`
- **Album** — `category` (FK), `name` (DA/EN), `description` (DA/EN), `slug`, `order`, `visible`, `cover_photo`
- **Photo** — `album` (FK), `image`, `order`, `caption` (DA/EN)
- **TimelineEntry** — `title` (DA/EN), `date`, `caption` (DA/EN), `slug`, `visible`, optional `tags` *(chosen from a shared `Tag` list, and admin text may hold links — see [ADR 0015](docs/decisions/0015-links-in-text-and-a-shared-tag-list.md); no link to a portfolio category, see [ADR 0016](docs/decisions/0016-the-timeline-stands-apart-from-the-portfolio.md))*
- **TimelineEntryPhoto** — `entry` (FK), `image`, `order`
- **PricingPackage** — `name` (DA/EN), `description` (DA/EN), `price`, `order`, `visible`
- **HomeSettings / AboutSettings / ContactSettings** — `django-solo` singletons holding the static per-language text for those pages
- **ClientGallery** — `slug` (random, unguessable), `label` (internal-only, owner's reference), `password_hash`, `created_at`, `expires_at`, `deleted` (tombstone flag, see §8)
- **GalleryPhoto** — `gallery` (FK), `image`, `order`
- **ContactSubmission** — a log of every contact-form submission, for the owner's own reference/audit trail; not required by the functional design, but included since it's a trivial model and a useful record to have

## Section-by-section implementation

### 1. Site-wide principles
- Visual tone and the "one deliberate accent" are carried by a shared base template and a
  small hand-written CSS file (CSS custom properties for color/type choices) — a design
  decision, not a technical one, so specifics are left to implementation time.
- Responsive layout via standard CSS (flexbox/grid + media queries) — no CSS framework
  dependency required.
- Language toggle: Django's built-in locale middleware plus its `set_language` view; the
  chosen language persists via the standard Django language cookie, so it carries across
  pages automatically.
- Images never served at original resolution publicly: enforced structurally — public views
  only ever reference the `easy-thumbnails`-generated derivative, never the original file
  path.
- Full nav reachability vs. unlisted pages: plain Django URL routing — nav-linked pages get
  normal named URLs; client-gallery and admin URLs exist but are never placed in any
  template's navigation, sitemap, or link graph.

### 2. Home page
- A single view rendering the `HomeSettings` singleton (hero image, tagline, links to
  Portfolio/Timeline/Contact). Optional teaser content (soft requirement) queries the most
  recent visible `Album` or `TimelineEntry`.

### 3. Portfolio page
- `Category` → `Album` → `Photo`, each admin-managed with ordering and a visible/draft flag
  (soft requirement) satisfied by the `visible` field, filtered out of public querysets when
  false.
- Lightbox viewer: [GLightbox](https://biati-digital.github.io/glightbox/) — a small,
  dependency-free lightbox library included via a plain `<script>`/`<link>` tag, no build
  step and no JS framework involved. Chosen over hand-rolling one from scratch since it's a
  solved problem with well-tested keyboard/touch/next-prev navigation already built in.
- Copy deterrents: CSS (`user-select: none`, disabling drag) plus a small JS handler
  suppressing the context menu on gallery images — a deterrent, not real protection, exactly
  as scoped in the functional design.

### 4. Timeline / showcase blog page
- `TimelineEntry` + `TimelineEntryPhoto`, rendered as a reverse-chronological list (default
  Django `ListView` ordering by `-date`). Optional tag field and optional `related_category`
  FK cover the two soft requirements directly.
- No comments/likes/accounts: nothing to build here — the omission is the implementation.

### 5. Pricing page
- `PricingPackage` rendered in `order`; static, no booking/payment logic anywhere in this
  view. FAQ blurb and per-package CTA (soft requirements) are just more admin-editable text
  fields on the same model/settings singleton.

### 6. Contact page
- A Django form with a hidden honeypot field (any non-empty value silently rejects without
  telling the sender why) and `django-ratelimit` capping submissions per IP per time window.
- On valid submission: `send_mail` through the configured relay to the owner's address, and
  a `ContactSubmission` row is written for the owner's own record-keeping.
- Success/failure is shown inline on the same page (no redirect-and-hope) so the visitor gets
  a clear result either way.

### 7. About page
- `AboutSettings` singleton (bio, photo, credentials, optional "how I work" section),
  editable the same way as Home/Contact.

### 8. Client delivery galleries

The most behaviorally distinct part of the system, matching the depth of functional design §8:

- **Creation**: an admin action on `ClientGallery` generates a random, URL-safe slug
  (`secrets.token_urlsafe`) and, unless the owner supplies one, a random plaintext password
  of the same kind. Only the **hash** of the password (`django.contrib.auth.hashers.make_password`)
  is stored — the plaintext is shown once, immediately after creation, in the admin UI
  (a one-time confirmation message), since it cannot be recovered afterward. "Regenerate
  password" (soft requirement) repeats this: new plaintext generated, shown once, hash
  replaces the old one.
- **Access flow**: visiting a gallery URL always shows a password prompt first — no gallery
  content is rendered before a password check succeeds. A correct password
  (`check_password` against the stored hash) sets a signed, gallery-scoped cookie
  (`django.core.signing`, scoped to that gallery's id/slug) so subsequent visits within the
  session don't need to re-enter the password. An incorrect password shows one generic error
  message regardless of the reason, per the functional requirement.
- **Serving files privately**: gallery images and the album ZIP are **not** placed under a
  publicly nginx-servable path the way public Portfolio/Timeline images are. Instead, the
  Django view re-checks the signed cookie on every request and, once satisfied, responds with
  an `X-Accel-Redirect` header pointing at an `internal`-only nginx location mapped to the
  real file on disk — nginx then serves the actual bytes efficiently, but that location is
  unreachable directly from the internet, so there is no way to guess a URL into a private
  gallery. Public Portfolio/Timeline derivatives, by contrast, are plain nginx-served static
  files, since they're public by design.
- **Full-album ZIP download**: built once, triggered by an explicit "Rebuild download ZIP"
  admin action on the gallery — not automatically on every save, since that would mean
  re-zipping the whole album on every minor edit for a gallery with many large photos. The
  built ZIP is cached alongside the gallery's images and served through the same
  `X-Accel-Redirect` mechanism as individual images. The admin action is a required step
  after uploading a gallery's photos, before sharing its link with the client.
- **Non-crawlable/non-indexable**: gallery views set an `X-Robots-Tag: noindex, nofollow`
  response header, and gallery URLs are simply never included in `sitemap.xml`. They are
  deliberately **not** listed in `robots.txt Disallow` either — doing so would itself publish
  the existence/URL-pattern of private galleries to anyone who reads that file, which defeats
  the purpose; omission plus the response header is the correct approach for genuinely
  unlisted content.
- **Expiry & deletion**: the scheduled `app-cron` job (see `architecture.md` §6) runs a
  management command that finds galleries past `expires_at` and:
  1. Deletes the gallery's image files and cached ZIP from disk (`shutil.rmtree` on its
     media subdirectory).
  2. Deletes the associated `GalleryPhoto` rows.
  3. Marks the `ClientGallery` itself as a **tombstone** (`deleted=True`, photos gone) rather
     than deleting it outright immediately — this lets the gallery's own URL keep responding
     with a clear "this gallery is no longer available" message (per the functional soft
     requirement) instead of a bare 404. A further cleanup pass, run by the same scheduled
     job, permanently deletes tombstoned rows 30 days after their expiry date — long enough
     for the "no longer available" message to do its job if a client returns late, short
     enough that nothing lingers indefinitely.
- **Admin visibility**: the default Django admin changelist for `ClientGallery` already
  satisfies "list of active galleries with expiry dates" (soft requirement); custom admin
  actions add "extend by N days," "expire now," and "regenerate password" as one-click
  operations.

### 9. Admin dashboard
- The Django admin site is mounted at a path read from an environment variable (not
  hardcoded, and not written down as a literal value in this document, since it functions as
  a shared secret alongside the account password — defense in depth on top of simply never
  linking to it), and protected by a single superuser account (`django.contrib.auth`). That
  account is created once, interactively, via
  `docker compose exec app python manage.py createsuperuser` during initial setup — not
  automated, since there is deliberately only ever the one.
- Every content type in §§2–8 above is managed through admin screens generated largely for
  free by Django; `django-modeltranslation` adds the DA/EN tabs automatically to each of
  them, and the ordering package adds drag-and-drop reordering — so no bespoke admin UI code
  is needed for any of the plain-CRUD content types. The only custom admin work is the
  gallery-specific actions described in §8.
- Bulk upload (soft requirement): a custom admin form accepting multiple files at once (a
  native multi-file `<input>`, no JS framework required) for both Portfolio albums and
  client galleries.

### 10. Cross-cutting requirements
- Non-crawlable client galleries and hard deletion on expiry are implemented as described in
  §8 — both are structural (there's no "hidden" state that still contains live data; expiry
  actually removes files from disk).
- No e-commerce/payments/print-ordering/visitor accounts: nothing to build — the absence of
  these features is a scope decision, not a gap.
- Single admin user: no Django permission-group complexity is introduced; one superuser is
  sufficient and matches the functional requirement directly.

## Deployment & operations

How this application is actually built, run, monitored, and backed up is covered in full in
`architecture.md` — this document intentionally doesn't repeat that ground. In short: the
app and its scheduled jobs run as two containers from the same image sharing the `/data`
volume described there; contact-form mail and error notifications both flow through the
mail-relay container described there.

## Open items for implementation time

These are deliberately left open rather than over-specified here:

- Exact visual design (colors, type pairing, the "one deliberate accent") — a design task,
  not an architectural one.
- Exact package minor/patch versions (major versions are pinned above) — pinned at
  implementation time, then maintained per `architecture.md` §10.
