# Defect register

Defects found by working through the running site and reading the repository. Each entry
records what is wrong, how it was observed, and what a fix would involve, so a fix can be
written without rediscovering the problem.

**Severity**

| | Meaning |
| --- | --- |
| **A** | Visitors see it, or it puts client data at risk. Fix before the VPS. |
| **B** | Wrong, but the damage is limited to search engines, the owner's own workflow, or polish. |
| **C** | Worth deciding on. Not obviously wrong, but not obviously right either. |

Four passes are recorded. The first (D1–D22) came from browsing the running site. The second
(D23–D33) came from reading every file in the repository afterwards, and found the more
serious problems — none of them visible from the outside. The third (D34–D38) came from
Anders working through a QA run book against a freshly rebuilt environment before 0.2.0, and
found what only someone using the site as its owner would notice. The fourth closed
the items the first had left open (D12–D22). The fourth (D39–D40) came
from running the 0.3.0 QA guide as commands rather than reading it, which is the cheapest of
the four and should probably have been the habit from the start.

| # | Sev | Defect | Status |
| --- | --- | --- | --- |
| [D1](#d1) | A | A template comment renders as visible text on every page | fixed |
| [D2](#d2) | A | Static assets cached `immutable` for 30 days under unhashed names | fixed |
| [D3](#d3) | A | `scripts/dev.sh` executes stray commands and exits 127 | fixed |
| [D4](#d4) | A | Private gallery pages and downloads send no `Cache-Control` | fixed |
| [D5](#d5) | A | The gallery password form has no rate limit | fixed |
| [D6](#d6) | B | `sitemap.xml` advertises `example.com` | fixed |
| [D7](#d7) | B | The sitemap omits every English page | fixed |
| [D8](#d8) | B | `robots.txt` points at a different host than the sitemap uses | fixed |
| [D9](#d9) | B | Contact notifications carry no `Reply-To` | fixed |
| [D10](#d10) | B | The contact notification email is hardcoded English | fixed |
| [D11](#d11) | B | The gallery ZIP is named after the random slug | fixed |
| [D12](#d12) | B | No meta description and no link-preview tags | fixed |
| [D13](#d13) | B | No favicon | fixed |
| [D14](#d14) | B | Photographs have no `width`/`height` | fixed |
| [D15](#d15) | B | Fonts are loaded from Google's CDN | fixed |
| [D16](#d16) | B | The admin is unbranded | fixed |
| [D17](#d17) | B | `verify.sh` never renders a page | fixed |
| [D18](#d18) | B | `<body class="">` on most pages | fixed |
| [D19](#d19) | C | No Content-Security-Policy | fixed |
| [D20](#d20) | C | Copy deterrents also apply to client galleries | fixed |
| [D21](#d21) | C | English URLs keep Danish slugs | fixed |
| [D22](#d22) | C | Portfolio photographs have no alt text of their own | fixed |
| [D23](#d23) | A | The test suite writes into the live data directory and deletes from it | fixed |
| [D24](#d24) | A | The rate limit is global, not per visitor | fixed |
| [D25](#d25) | A | The recorded visitor address is chosen by the visitor | fixed |
| [D26](#d26) | A | Deleting galleries in bulk leaves the photographs on disk | fixed |
| [D27](#d27) | B | The Danish catalogue was missing 123 strings | fixed |
| [D28](#d28) | B | `$host` drops the port from every absolute URL | fixed |
| [D29](#d29) | B | The sitemap lists albums inside unpublished categories | fixed |
| [D30](#d30) | B | Error emails are sent while developing | fixed |
| [D31](#d31) | B | The portfolio index throws away its own prefetch | fixed |
| [D32](#d32) | B | Non-ASCII download filenames are mangled | fixed |
| [D33](#d33) | C | The admin changelist can raise on a half-built ZIP | fixed |
| [D34](#d34) | B | The admin's section headings are in English | fixed |
| [D35](#d35) | B | The enquiry button does not say which package it is for | fixed |
| [D36](#d36) | B | Right-click is not blocked on the lightbox image | fixed |
| [D37](#d37) | B | The header holds the top of a phone screen | fixed |
| [D38](#d38) | C | Leaving the site costs you the page you were reading | fixed |
| [D39](#d39) | B | `dev.sh reset` and `down` leave containers running | fixed |
| [D40](#d40) | B | Private gallery files are not marked `noindex` | fixed |

---

## Fourth pass: found by running the 0.3.0 QA guide

Two findings, both from mechanically running the checks rather than reading them. D39 came
from Anders's own run; D40 from proving a check before publishing it.

### D39

**`dev.sh reset` and `dev.sh down` left containers running.** Compose only acts on services
the current file describes and whose profile is active, so a container created under an older
service name is walked straight past — and so is one behind an inactive profile, which is not
an "orphan" either and survives `--remove-orphans`. Renaming the mail relay to `mailpit` and
`postfix` in 0.3.0 made this visible in both directions: reset on `main` left `mailpit`
running, reset on the branch left `mail-relay` running. The survivor then held the network
open, so that could not be removed either, and a "reset" left a container attached to the
tree it had just deleted. *Fixed*: both commands now enumerate the compose file's profiles
with `docker compose config --profiles` and pass `--remove-orphans`, so they mean everything.

### D40

**Private gallery files were not marked `noindex`; the page around them was.** Django calls
`noindex()` on every gallery response, setting `X-Robots-Tag` and `Cache-Control`. When that
response is an X-Accel-Redirect, nginx takes over and serves the file itself, forwarding only
a fixed set of upstream headers — `Content-Type`, `Content-Disposition` and `Cache-Control`
survive, arbitrary ones do not. So the gallery page carried the marking and the photographs
and ZIP inside it did not, which is the wrong way round: the files are the private part.
Low severity, since reaching them needs the password and they are linked from nowhere, but it
was a stated intention that silently did not hold. *Fixed*: the `internal` location restates
the header.

---

## Third pass: found by using the site as its owner

Five findings from a teardown-and-rebuild QA walkthrough before 0.2.0 — 40 checks, both
languages, every page type and all three gallery states. Everything the first two passes
covered still held; these are the things only someone operating the site would hit.

### D34

**The admin's section headings are in English.** The index page read "Galleries", "Pages",
"Portfolio", "Timeline" while everything beneath them was Danish. Django falls back to the
raw app label when an app declares no `verbose_name`, and none of the five apps did — so the
one part of the admin D27's translation pass could not reach was the first thing you see.
*Fixed*: each app names itself, translated.

### D35

**The enquiry button does not say which package it is for.** The pricing page has linked to
the contact form as `?type=<package name>` since it was written, and the view never read the
parameter, so an enquiry arrived with no indication of what prompted it. *Fixed*: it prefills
the shoot type as an initial value only — the visitor can edit or clear it, and a submitted
value always wins. Three tests cover it.

### D36

**Right-click is not blocked on the lightbox image.** The deterrent was bound to each image
at load, so it covered the grid thumbnails and missed the lightbox, which builds its own
overlay outside the photo grid — and shows the *largest* public derivative. The one image
worth deterring was the one left unprotected. The portfolio index and category pages had
never opted in at all.

*Fixed* by delegating from the document instead. It remains a speed bump rather than
protection: the lightbox link points at a real image URL, and the bytes are on the wire
either way. Anders's judgement was that this is proportionate — he is not publishing work he
is that sensitive about.

### D37

**The header holds the top of a phone screen.** It was `position: sticky` and two lines
tall, so on a phone it kept a noticeable share of the screen through every scroll — space a
photography site should be giving to the photographs. *Fixed*: below 760px it scrolls away
with the page and drops the tagline, which the home page carries anyway.

### D38

**Leaving the site costs you the page you were reading.** Social links and calls to action
opened in the same tab, including the pricing enquiry button — which took away the prices
the visitor was in the middle of comparing. *Fixed*: things a visitor *does* open a tab;
things they *navigate to* do not, so the main navigation is unchanged.

---

## Second pass: found by reading the repository

These are the ones that mattered. Every one of them passed `scripts/verify.sh`, and none
was visible from the browser.

### D23

**The test suite writes into the live data directory and deletes from it.** `MEDIA_ROOT` was
never overridden for tests, so `make_gallery()` wrote real JPEGs into
`data/media/galleries/` and left them there — 283 directories on disk against 2 rows in the
database.

The litter was the harmless half. The gallery tests exercise `expire_now()`, which calls
`shutil.rmtree()` on a path built from the gallery's slug. Those tests were running
`rmtree` against the same tree that holds real client photographs, separated from them only
by the slugs happening not to collide. Django swaps the database out for a test run and says
nothing about the filesystem, so the isolation had to be arranged deliberately and had not
been.

*Fixed* by `config.test_runner.IsolatedDataRunner`, which points `DATA_ROOT`, `MEDIA_ROOT`
and the thumbnail cache at a temporary directory for the run and removes it afterwards.
`galleries/thumbnails.py` also had to stop building its storage at import time, which
captured whatever `MEDIA_ROOT` was when the module was first loaded and ignored every later
change. Verified: a full run leaves the live tree at exactly the file count it started with.

The 283 existing directories are still there. They are inert, and `scripts/dev.sh reset`
clears them along with everything else; nothing in this branch touches them.

### D24

**The rate limit is global, not per visitor.** Every request reaches the application from
nginx's container address:

```
app-1  | 172.18.0.4 - - [13/Sep/2026:17:18:20] "GET /priser/ HTTP/1.0" 200
```

`django_ratelimit` with `key="ip"` reads `REMOTE_ADDR`, which was therefore identical for
every visitor on earth. `CONTACT_RATELIMIT=5/h` did not mean five messages per sender; it
meant **five messages per hour in total**, after which the contact form refused everyone.
One bot, or one person retrying, would have closed the site's only enquiry route for an
hour — and nothing would have looked broken.

*Fixed* by `core.middleware.ClientIPMiddleware`. See D25 for why it reads the header the way
it does.

### D25

**The recorded visitor address is chosen by the visitor.** `_client_ip()` took the *first*
entry of `X-Forwarded-For`. nginx sets that header with `$proxy_add_x_forwarded_for`, which
is *whatever the caller sent* with the real address appended — so the first entry is
attacker-controlled and the last one is ours. Demonstrated before the fix:

```
$ curl -H "X-Forwarded-For: 203.0.113.99" ... /kontakt/
  stored ip: 203.0.113.99
```

The address stored against a submission, and logged when the honeypot fires, is the one
record that would identify an abusive sender. It was worthless.

*Fixed* by counting in from the trusted end: `TRUSTED_PROXY_COUNT` (default 1, an
environment variable because a CDN would make it 2) says how many hops belong to us, and the
entry that many from the right is the real caller. A forged entry can only ever land further
left. The same request now records `192.168.65.1`, the real peer.

### D26

**Deleting galleries in bulk leaves the photographs on disk.** `ClientGallery.delete()`
removes the files, with a comment saying that deleting from the admin should not orphan
them. But the admin's "Delete selected" calls `ModelAdmin.delete_queryset()`, which runs
`queryset.delete()` — and a queryset delete does **not** call each model's `delete()`. So the
one path the comment was written for was the one path that skipped it: rows vanished from the
admin while the client's photographs stayed on disk indefinitely. For expired client work
that is the outcome `functional_design.md` §10 exists to prevent.

*Fixed* by overriding `delete_queryset`, with a test that deletes through the admin code path
and asserts the directory is gone.

### D27

**The Danish catalogue was missing 123 strings.** `makemessages` had not been run across the
current code, so the catalogue knew 47 strings while the codebase contained 170. Everything
missing was untranslated at runtime, which meant the whole admin — every model name, field
label and help text, every action — rendered in English for a Danish user. My first pass
reported "0 untranslated" and was wrong: the strings were not untranslated, they were absent,
and I had checked the wrong thing.

A further 19 entries were marked `fuzzy`, which gettext ignores at runtime, and the guesses
were wrong where it mattered — `client gallery` had been matched to *"Åbn galleri"* ("Open
gallery"), and `Contact form: %(name)s` to *"Billeder til %(name)s"* ("Photos for %(name)s").

*Fixed*: catalogue regenerated, all 104 empty entries translated, all 19 fuzzy entries
corrected and unfuzzied, and the plural of "album" corrected from *"albums"* to *"albummer"*.
Catalogue is now 0 untranslated, 0 fuzzy. **The Danish wording is worth your review** — it is
the one part of this branch that is a judgement call rather than a verifiable fix.

### D28

**`$host` drops the port from every absolute URL.** `proxy_set_header Host $host` strips any
port, so Django built absolute URLs — sitemap entries, the `robots.txt` sitemap line, and any
password-reset link later — pointing at a port nothing listens on:

```
<loc>http://localhost/priser/</loc>      # the site is on :8080
```

Invisible in production on 443, wrong everywhere else, including any future staging host on a
non-standard port. *Fixed* by using `$http_host`, which preserves what the client actually
asked for.

### D29

**The sitemap lists albums inside unpublished categories.** `AlbumSitemap` filtered on the
album's own `visible` flag but not its category's, while the album *view* requires both. So a
published album in a draft category was advertised at a URL that answers 404 — and its name
and slug were published while the owner was still preparing it, which is what marking a
category hidden is for. *Fixed*, with a test.

### D30

**Error emails are sent while developing.** The `mail_admins` handler lacked the
`require_debug_false` filter that Django's own default configuration applies, so every error
raised with `DEBUG=1` — including ones being caused deliberately — was mailed to the owner.
*Fixed.*

### D31

**The portfolio index throws away its own prefetch.** The view did
`prefetch_related("albums")`; the template then called `category.visible_albums.first` and
`category.visible_albums.count`, each a fresh queryset. The prefetch was never used and each
category cost two extra queries on top of it. *Fixed* with a `Prefetch(..., to_attr=...)` the
template reads directly. Verified the rendered counts still match the database.

### D32

**Non-ASCII download filenames are mangled.** The X-Accel branch built
`Content-Disposition` with a raw f-string, leaving Django to MIME-encode anything outside
latin-1 into a `=?utf-8?b?…?=` word that browsers show verbatim; a `"` in a filename would
break the header's quoting outright. Danish filenames routinely contain æ, ø and å. *Fixed*
with RFC 6266 encoding — a stripped ASCII `filename` plus a percent-encoded `filename*`.

### D33

**The admin changelist can raise on a half-built ZIP.** `zip_state` called
`obj.zip_built_at.strftime(...)` whenever the file existed, but the file and the timestamp
can disagree — a restore from backup brings one back without the other, as does a crash
between writing the archive and saving the row. In that state the gallery changelist raises
`AttributeError` and becomes unreachable. *Fixed* by reporting the file as present when the
date is unknown.

---

## First pass: found by browsing the site

### D1

**A template comment rendered as visible text on every page.** `base.html` opened a
`{# … #}` comment that ran onto a second line. Django's `{# #}` is a **single-line**
construct; a multi-line one is not recognised, so the text was emitted into the HTML, inside
`<nav>`, on all 34 pages. *Fixed* by using `{% comment %}`, here and in the one other place
with the same pattern.

### D2

**Static assets were cached `immutable` for 30 days under unhashed filenames.** `immutable`
promises a browser that the bytes at a URL will never change. That is true under
`ManifestStaticFilesStorage` (`DEBUG=0`, hashed filenames) and false in development, where
the filename is plain `/static/css/site.css`. Browsers that had fetched the terracotta
stylesheet would not re-request it for a month, and no ordinary reload helped — which is why
the site still looked unchanged after Atelier Sage shipped.

*Fixed*: the policy is now `STATIC_CACHE_CONTROL`, defaulting to
`public, max-age=0, must-revalidate`, with the production value documented beside it. The old
config also emitted two conflicting `Cache-Control` headers, from `expires` and `add_header`
both; there is now one.

### D3

**`scripts/dev.sh` executed stray commands and exited 127.** `dev.sh` sources `.env`, and the
cron schedules were unquoted:

```
CRON_SCHEDULE_EXPIRE_GALLERIES=0 3 * * *
```

Bash reads that as an assignment of `0` prefixed to the command `3 * * *`, with the asterisks
globbed against the repository. Under `set -euo pipefail` the script then **aborted**: `dev.sh
urls` printed nothing and returned 127, and `dev.sh up` started the containers and died
before waiting for health or printing any URL. *Fixed* by quoting the values — compose strips
the quotes, so the containers see exactly what they saw before.

### D4

**Private gallery pages and downloads sent no `Cache-Control`.** Nothing stopped a shared
proxy, or a browser on a shared machine, keeping a copy of a client's gallery long after it
had expired and been deleted from disk. *Fixed*: every private response now carries
`private, no-store`, with tests on the page, the photo download and the ZIP.

### D5

**The gallery password form had no rate limit**, while the contact form did. Guessing a
generated password is hopeless, but an unthrottled endpoint that checks a credential is worth
closing. *Fixed* via `GALLERY_UNLOCK_RATELIMIT` (default `20/h` — generous, because a client
mistyping a pasted password must not be locked out).

### D6, D7, D8

**The sitemap advertised `example.com`, omitted every English page, and disagreed with
`robots.txt` about the host.** The first was `django.contrib.sites` with its unconfigured
default domain. Rather than add another value to remember per environment, the sites
framework has been dropped: Django then derives the domain from the request, which is correct
everywhere with nothing to configure and agrees with `robots.txt` by construction. `i18n` and
`alternates` on the sitemaps add the English URLs with reciprocal `hreflang`. Combined with
D28, the sitemap now reports the right host *and* port.

`robots.txt` still says `Allow: /` and does not mention the gallery prefix. That is
deliberate and unchanged: listing it would advertise the path, and `noindex` plus
`X-Robots-Tag` already do the work.

### D9, D10, D11

**Contact notifications had no `Reply-To`, were hardcoded English, and gallery ZIPs were named
after the random slug.** All three fixed: replying to an enquiry now reaches the enquirer, the
notification is translated, and the client's archive is called `sofie-jonas.zip` rather than
`wMbTQ8P0ZLTr4M93MlXKoQ.zip`.

### D17

**`verify.sh` never rendered a page**, which is how a stray comment shipped on all 34 of
them. *Fixed* by `core.tests.RenderedPageTests`, which walks the public URLs in both
languages and asserts no response contains `{#`, `{%` or `{{`. That test fails against the
previous commit.

---

## Fourth pass: the items left open

D12–D22 were first recorded as features or judgement calls and left. All were closed
before 0.4.0, because two of them only get more expensive after launch: addresses that
search engines have indexed, and photographs uploaded without a description.

### D12

**No meta description and no link-preview tags.** A link to an album pasted into a message
arrived as a bare URL with no image. *Fixed*: every public page carries a description and
Open Graph tags, with the album cover or first photograph as the preview and the front
page's hero as the fallback. Gallery and error pages carry none.

### D13

**No favicon.** *Fixed*: an SVG mark in the accent colour, linked from every page;
`/favicon.ico` redirects to it for the clients that ask there regardless.

### D14

**Photographs have no `width`/`height`.** *Fixed*: public images carry their derivative's
pixel size, remembered in the database (`THUMBNAIL_CACHE_DIMENSIONS`) so nothing opens a
file to find out. Client-gallery images are sized by the CSS grid's `aspect-ratio`.

### D15

**Fonts are loaded from Google's CDN**, disclosing every visitor's address to a third
party. *Fixed*: Fraunces and Inter are served from `static/fonts/`, with their licences.

### D16

**The admin is unbranded.** *Fixed*: it is headed "Lauridsen Fotos".

### D18

**`<body class="">`** on pages that set no class. *Fixed*: the block now carries the whole
attribute, so a page without one emits a bare `<body>`.

### D19

**No Content-Security-Policy.** *Fixed*: every page sends one that names no host but the
site itself, with no inline script allowed. It is a setting (`DJANGO_CSP`), and can be sent
report-only. Styles still allow inline: the lightbox needs it.

### D20

**Copy deterrents also apply to client galleries** — the photographs the client is meant
to save. *Fixed*: deterrents are scoped to public pages.

### D21

**English URLs keep Danish slugs.** *Fixed*: `/en/pricing/`, `/en/contact/`, `/en/about/`.
The Danish addresses are unchanged. Decided now because an address is free to change only
until someone has linked to it.

### D22

**Portfolio photographs have no alt text of their own.** *Fixed*: portfolio and timeline
photographs have a translated alt-text field beside the caption; the caption stands in
when it is empty.

---

## Checked and found correct

Recorded so they are not re-examined later:

- All 77 public URLs and 55 referenced assets return 200 in both languages.
- Client galleries: the gate reveals no filenames or counts; an expired gallery returns 410
  with the tombstone; the unlock cookie is signed, `HttpOnly`, `SameSite=Lax` and scoped to
  `Path=/g/<slug>/`; `secure` follows `DEBUG`; per-photo and ZIP downloads work through
  X-Accel-Redirect; `noindex, nofollow, noarchive` is present as both meta tag and header on
  every gallery state; galleries appear in neither the sitemap nor `robots.txt`.
- **Private gallery thumbnails do not leak into the publicly served cache.** They are written
  under `MEDIA_ROOT`, which nginx does not serve; `find data/cache -ipath '*galler*'` is empty.
- The gallery unlock cookie is scoped per gallery, so one gallery's cookie cannot open another.
- `protected_file_response` refuses any path resolving outside `DATA_ROOT`.
- The DA → EN → DA language chain works, including from a page already under `/en/`, and
  gallery pages honour the language cookie despite having no language prefix.
- Public derivatives carry no EXIF.
- SQLite really is in WAL mode with `synchronous=NORMAL` — the two-statement `init_command`
  is applied, not silently dropped.
- `/app/cron.env` is written with `declare -x`, so it is properly quoted and the scheduled
  jobs do not suffer the `.env` problem from D3. The rendered crontab matches `.env`.
- Copy deterrents are wired correctly on portfolio *and* timeline pages (`protect-images`
  comes from `body_class`, which is easy to miss when reading the rendered markup).
- The `static_files` named volume is refreshed by `collectstatic --clear` in the entrypoint,
  so a rebuilt image's assets really are served.
- `.env` and `.env.example` define exactly the same keys.
- No duplicate `id` attributes; no leaked template syntax anywhere, now enforced by a test.
- **Every process in the app container runs as uid 1000, PID 1 included** — confirmed with
  `docker compose top app` and `/proc/1/status`. The QA step that first appeared to fail here
  was a bad instruction, not a finding: the image is slim and has no `ps`. An `exec` shell
  still enters as root, because privileges are dropped by the entrypoint rather than by a
  `USER` line in the Dockerfile.
- A cold start from `scripts/dev.sh reset` reaches a serving site in about nine seconds, and
  the seeded environment answers on all its public URLs with no broken assets.

## Known and already tracked

- Custom 404 and 500 pages do not exist yet — a definition-of-done item for
  [ROADMAP 0.3.0](../ROADMAP.md#030--production-configuration-proven-locally).
- HSTS and TLS are absent because there is no domain yet — ROADMAP 0.5.0.
- `app-cron` still runs a root PID 1, because the cron daemon must be root to drop to `app`.
  Raised during the PR #2 review; `supercronic` would remove it. Undecided.
