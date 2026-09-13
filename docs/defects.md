# Defect register

Defects found by working through the running site rather than by reading the code. Each entry
records what is wrong, how it was observed, and what a fix would involve, so a fix can be
written without rediscovering the problem.

Found against `feat/visual-direction` (commit `ec03162`) running locally on Docker Compose;
every defect was also confirmed present on `main` unless the entry says otherwise.

**Severity**

| | Meaning |
| --- | --- |
| **A** | Visitors see it, or it puts client data at risk. Fix before the VPS. |
| **B** | Wrong, but the damage is limited to search engines, the owner's own workflow, or polish. |
| **C** | Worth deciding on. Not obviously wrong, but not obviously right either. |

Status is `open` until a fix merges, then the PR number goes in the status column.

| # | Severity | Defect | Status |
| --- | --- | --- | --- |
| [D1](#d1) | A | A template comment renders as visible text on every page | open |
| [D2](#d2) | A | Static assets are cached `immutable` for 30 days under unhashed names | open |
| [D3](#d3) | A | `scripts/dev.sh` executes stray commands and loses two variables | open |
| [D4](#d4) | A | Private gallery pages and downloads send no `Cache-Control` | open |
| [D5](#d5) | A | The gallery password form has no rate limit | open |
| [D6](#d6) | B | `sitemap.xml` advertises `example.com` | open |
| [D7](#d7) | B | The sitemap omits every English page | open |
| [D8](#d8) | B | `robots.txt` points at a different host than the sitemap uses | open |
| [D9](#d9) | B | Contact notifications carry no `Reply-To` | open |
| [D10](#d10) | B | The contact notification email is hardcoded English | open |
| [D11](#d11) | B | The gallery ZIP is named after the random slug | open |
| [D12](#d12) | B | No meta description and no link-preview tags | open |
| [D13](#d13) | B | No favicon | open |
| [D14](#d14) | B | Photographs have no `width`/`height`, so the page reflows as they load | open |
| [D15](#d15) | B | Fonts are loaded from Google's CDN | open |
| [D16](#d16) | B | The admin is unbranded | open |
| [D17](#d17) | B | `verify.sh` never renders a page, so none of this was caught | open |
| [D18](#d18) | B | `<body class="">` on most pages | open |
| [D19](#d19) | C | No Content-Security-Policy | open |
| [D20](#d20) | C | Copy deterrents also apply to client galleries | open |
| [D21](#d21) | C | English URLs keep Danish slugs | open |
| [D22](#d22) | C | Portfolio photographs have no alt text of their own | open |

---

## A — visitor-visible or client-data risk

### D1

**A template comment renders as visible text on every page.**

`src/templates/base.html:38` opens a `{# … #}` comment that runs onto a second line:

```
{# One form per language: each carries its own already-translated target, since
   set_language cannot work that out for a URL in a non-default language. #}
```

Django's `{# #}` is a **single-line** construct. A multi-line one is not recognised, so the
text is emitted into the HTML verbatim. It sits inside `<nav>`, next to the language buttons,
on every page of the site — 34 pages crawled, 34 affected. This is the stray text visible in
the browser.

`src/templates/galleries/unavailable.html:4` has the same multi-line pattern. It happens to be
harmless: it sits outside any `{% block %}` in a template that extends `base.html`, and Django
discards that text. It is the same latent mistake and should be fixed alongside.

*Fix*: use `{% comment %}…{% endcomment %}` for anything spanning more than one line. The three
single-line `{# #}` comments elsewhere in the templates are fine as they are.

### D2

**Static assets are cached `immutable` for 30 days under unhashed filenames.**

`docker/nginx/templates/default.conf.template:22-23`:

```nginx
expires 30d;
add_header Cache-Control "public, immutable";
```

With `DJANGO_DEBUG=1` the filename is plain `/static/css/site.css` — no content hash. `immutable`
is a promise to the browser that the bytes at that URL will *never* change, so a browser that
fetched the terracotta stylesheet will not re-request it for 30 days, and no ordinary reload
will dislodge it. **This is why the site still showed the old palette after Atelier Sage was
deployed.** The server is serving the correct file:

```
$ curl -s localhost:8080/static/css/site.css | grep accent
  --accent: #5e7356;
```

`immutable` is only safe when the URL changes whenever the content does. That is true under
`ManifestStaticFilesStorage` (`DEBUG=0`, hashed filenames) and false in development.

Separately, `expires 30d` and the `add_header` each emit their own header, so responses carry
two `Cache-Control` lines.

*Fix*: make the caching policy depend on whether filenames are hashed — a short `max-age` with
revalidation in development, `immutable` only when `DJANGO_DEBUG=0`. Since the nginx config is
already an envsubst template, this belongs in an environment variable with a documented default
rather than a literal, per the "nothing operational is hardcoded" rule in `CLAUDE.md`.

*Immediate workaround*: a hard reload (Cmd-Shift-R) or an empty-cache reload picks up the
current stylesheet.

### D3

**`scripts/dev.sh` executes stray commands and loses two variables.**

Every invocation prints:

```
./.env: line 44: 3: command not found
./.env: line 45: 3: command not found
```

`dev.sh:32-34` does `set -a; . ./.env`, which runs the file as shell. The cron schedules are
unquoted:

```
CRON_SCHEDULE_EXPIRE_GALLERIES=0 3 * * *
```

Bash reads that as the assignment `CRON_SCHEDULE_EXPIRE_GALLERIES=0` *prefixed to the command*
`3 * * *` — so it tries to run a program called `3`, with the asterisks glob-expanded against
the repository root. Both variables end up unset in the script's environment:

```
$ bash -c 'set -a; . ./.env; echo "[${CRON_SCHEDULE_EXPIRE_GALLERIES:-UNSET}]"'
[UNSET]
```

`docker compose` reads `.env` with its own parser, not a shell, so the containers are unaffected
— the rendered `/etc/cron.d/app-jobs` is correct and `/app/cron.env` is properly quoted
(`declare -x`). The damage is confined to `dev.sh`, but it is confined only by luck: any future
use of those variables inside the script would silently get nothing.

*Fix*: quote the values in `.env` and `.env.example` (compose strips surrounding quotes, so the
containers are unaffected — worth confirming when fixing), or stop sourcing `.env` in `dev.sh`
and parse it safely. Quoting is the smaller change and fixes the class of problem for every
value containing whitespace or a glob character.

### D4

**Private gallery pages and downloads send no `Cache-Control`.**

```
$ curl -sI localhost:8080/g/<slug>/
X-Robots-Tag: noindex, nofollow, noarchive
X-Frame-Options: DENY
...no Cache-Control at all
```

The same is true of `/g/<slug>/download/` (the ZIP) and `/g/<slug>/p/<id>/download/`. The
noindex posture is solid — both the meta tag and the header are present on the gate, the
unlocked gallery and the tombstone — but nothing tells a cache not to store the response.
Client photographs and the gallery page can therefore be written to a shared proxy cache or
persist in the browser cache on a shared machine after the gallery expires. `functional_design.md`
§10 treats actual removal of expired client images as a data-retention requirement; a cached
copy is a hole in that.

*Fix*: `Cache-Control: private, no-store` on the gallery views and on the X-Accel-Redirect
responses.

### D5

**The gallery password form has no rate limit.**

`src/pages/views.py` rate-limits the contact form via `django_ratelimit`. `src/galleries/views.py`
does not reference it at all, so password attempts against `/g/<slug>/` are unthrottled.

The passwords are generated with `secrets` and have enough entropy that guessing is not a
realistic attack, and the slug has to be known first — so this is not urgent. But an unthrottled
POST that checks a credential is worth closing, and the mechanism is already in the project.

*Fix*: apply the same `is_ratelimited` treatment, keyed on IP and gallery slug, with the rate in
`.env` beside `CONTACT_RATELIMIT`.

---

## B — wrong, but limited damage

### D6

**`sitemap.xml` advertises `example.com`.**

```xml
<url><loc>http://example.com/priser/</loc>…
```

`SITE_ID = 1` is set in `src/config/settings.py:120`, but the `django.contrib.sites` row is
still Django's default `example.com`. Every URL in the sitemap points at a domain that is not
this site.

*Fix*: set the `Site` domain and name from an environment variable — a data migration or a
startup step, so it is correct on the VPS without anyone editing a database row by hand.

### D7

**The sitemap omits every English page.** It lists 17 Danish URLs and no `/en/` URL. The
`xmlns:xhtml` namespace is declared on `<urlset>` but never used, so there are no
`hreflang` alternates either. The English half of the site is invisible to search engines.

*Fix*: emit both languages, with reciprocal `<xhtml:link rel="alternate" hreflang="…">` on each
entry.

### D8

**`robots.txt` points at a different host than the sitemap uses.**

```
Sitemap: http://localhost/sitemap.xml
```

The port is missing (so the link is wrong even locally), and the host is derived from the
request while the sitemap's own URLs come from the `Site` record — the two disagree by
construction. Fixing D6 should make both read from the same source.

Note that `robots.txt` says `Allow: /` and does not mention the gallery prefix. That is
deliberate and correct: listing it would advertise the path, and `noindex` plus `X-Robots-Tag`
already do the work (verified present on all three gallery states). No change wanted here.

### D9

**Contact notifications carry no `Reply-To`.** The owner receives mail from
`no-reply@lauridsen-fotos.local` with the sender's address only in the body, so hitting Reply
goes nowhere:

```
From    : no-reply@lauridsen-fotos.local
ReplyTo : []
```

For the site's one lead-generation feature this is a real workflow defect.

*Fix*: `EmailMessage(..., reply_to=[form.cleaned_data["email"]])`.

### D10

**The contact notification email is hardcoded English**, while the site, the owner and most
submissions are Danish:

```
Subject: Contact form: Defect Test
Name:     …
Email:    …
Type:     —
```

*Fix*: translate the notification, or deliberately pin it to one language and say so.

### D11

**The gallery ZIP is named after the random slug.** The client saves
`wMbTQ8P0ZLTr4M93MlXKoQ.zip`. It should carry the gallery or client name — this is the file the
client keeps.

*Fix*: derive the filename from the gallery title, slugified, with the token as a fallback.

### D12

**No meta description and no link-preview tags.** Every page carries exactly two `<meta>` tags,
`charset` and `viewport`. There is no `description`, and no Open Graph or Twitter card tags — so
a link to an album shared on Instagram, Facebook or in a message renders as a bare URL with no
image. For a photography business whose work is the product, that is a meaningful loss.

*Fix*: a `description` block in `base.html` fed per page, plus `og:title`, `og:description`,
`og:image` (the album cover or hero) and `og:type`.

### D13

**No favicon** — `/favicon.ico` returns 404 and no `<link rel="icon">` is emitted.

### D14

**Photographs have no `width`/`height`**, so the page reflows as each one loads. On the album
page, 0 of 6 images carry dimensions. The thumbnailer knows the dimensions at render time.

*Fix*: emit `width` and `height` from the thumbnail object; CSS already handles the display
size, and the attributes only supply the aspect ratio.

### D15

**Fonts are loaded from Google's CDN** (`base.html:8-10`). Two consequences: every visitor's IP
is disclosed to Google, which for an EU business is a live GDPR question and has been litigated
in Germany; and the site's typography depends on a third party being reachable. These are the
only external requests the site makes apart from the Instagram link.

*Fix*: self-host the Fraunces and Inter woff2 files under `src/static/`. This also removes a
render-blocking third-party request. It stays within `technical_design.md`'s no-bundler rule —
the files are static assets, not a build step.

### D16

**The admin is unbranded** — the login page reads *"Log ind | Django website-administration"*.
`site_header`, `site_title` and `index_title` are unset. Cosmetic, but this is the interface the
owner uses.

### D17

**`verify.sh` never renders a page, so none of this was caught.** The pipeline passes cleanly on
the current tree:

```
VERIFICATION PASSED
```

It runs Django's system checks, the migration check, the test suite and a compose validation —
but nothing fetches a URL and looks at the output, which is why a stray template comment could
ship on every page.

*Fix*: a smoke test that walks the public URLs and asserts, at minimum, that no response body
contains `{#`, `{%` or `{{`; and header assertions for the defects above once they are fixed.
That converts most of this register into something that cannot silently regress.

### D18

**`<body class="">`** is emitted on every page that does not set `body_class` — a leftover from
removing the theme switcher. Harmless, but it is the kind of thing that suggests a template is
half-finished.

---

## C — decisions, not clearly defects

### D19

**No Content-Security-Policy.** `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`
and `Cross-Origin-Opener-Policy` are all set; CSP is absent. It is the one header that would
contain the damage from an injected script. Worth adding, and much easier to write once D15
removes the external font requests.

### D20

**Copy deterrents also apply to client galleries.** `site.js:38-40` blocks `contextmenu` and
`dragstart` on `.photo--client` images — the photographs the client is specifically meant to
save. They have explicit download buttons, so nothing is blocked outright, but right-click-save
is how many people expect to do it. Deterrents make sense on the public portfolio, where the
point is to slow casual copying; inside a paid delivery gallery they only get in the client's
way. Suggest scoping them to public pages.

### D21

**English URLs keep Danish slugs** — `/en/priser/`, `/en/om/`, `/en/portfolio/bryllup/`. Django
supports translated URL patterns. Whether it is worth the extra surface is a judgement call;
noting it so the decision is deliberate.

### D22

**Portfolio photographs have no alt text of their own.** The template does the right thing —
`alt="{{ photo.caption }}"` — but `caption` is a visible caption, not a description, and the
demo content leaves it empty, so every portfolio image currently renders `alt=""`. A caption and
an alt text are different things: one is shown, the other describes the image to someone who
cannot see it. `ROADMAP.md` already lists an accessibility pass after 1.0; the model question
(one field or two) is worth settling before there is much content to retrofit.

---

## Checked and found correct

Recorded so they are not re-examined later:

- All 34 public pages and 55 referenced assets return 200 in both languages; no broken links or
  images.
- The DA → EN → DA language chain works, including from a page already under `/en/`.
- Client galleries: the gate returns 200 and reveals no filenames or counts; an expired gallery
  returns 410 with the tombstone; the unlock cookie is `HttpOnly`, `SameSite=Lax`, signed, and
  scoped to `Path=/g/<slug>/`; per-photo and full-ZIP downloads both work through
  X-Accel-Redirect; `noindex, nofollow, noarchive` is present as both a meta tag and a header on
  every gallery state.
- Gallery pages honour the language cookie despite having no language prefix.
- The contact form submits, shows the success notice, and the mail arrives at the relay.
- Public derivatives carry no EXIF.
- Copy deterrents are wired correctly on portfolio *and* timeline pages (`protect-images` comes
  from `body_class`, which is easy to miss when reading the rendered markup).
- The `static_files` named volume is refreshed by `collectstatic --clear` in the entrypoint, so a
  rebuilt image's assets really are served — the stale-CSS problem in D2 is in the browser, not
  the volume.
- `.env` and `.env.example` define exactly the same keys.
- The Danish translation catalogue has no untranslated and no fuzzy entries.
- No duplicate `id` attributes; no other leaked template syntax anywhere.

## Known and already tracked

- Custom 404 and 500 pages do not exist yet; `DEBUG=1` locally shows Django's debug pages. This
  is a definition-of-done item for [ROADMAP 0.3.0](../ROADMAP.md#030--production-configuration-proven-locally).
- HSTS and TLS are absent because there is no domain yet — ROADMAP 0.5.0.
- `app-cron` still runs a root PID 1, because the cron daemon must be root to drop to `app`.
  Raised during the PR #2 review; `supercronic` would remove it. Undecided.
