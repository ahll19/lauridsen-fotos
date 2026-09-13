# Lauridsen Fotos

Photography portfolio and client delivery site: a public portfolio, a photo-led timeline,
static pricing/contact/about pages, and private client galleries that delete themselves when
they expire.

Django 5.2 on Python 3.12, behind nginx, on a single Docker Compose stack. No JavaScript build
step, no framework — server-rendered templates, hand-written CSS, and one small lightbox
library.

This README is the operating manual: how to set it up, and how to do the things you will
actually do. It assumes you have been away from the code for a few months and want to publish
an album without reading anything else.

---

## Contents

- [First time on a machine](#first-time-on-a-machine)
- [Everyday commands](#everyday-commands)
- [Running the site](#running-the-site)
- [Publishing: the things you do most](#publishing-the-things-you-do-most)
- [Client galleries, start to finish](#client-galleries-start-to-finish)
- [Changing how it is configured](#changing-how-it-is-configured)
- [Working on the code](#working-on-the-code)
- [Cutting a release](#cutting-a-release)
- [When something is wrong](#when-something-is-wrong)
- [How it is laid out](#how-it-is-laid-out)
- [The design documents](#the-design-documents)

---

## First time on a machine

You need Docker Desktop (or Docker Engine with the Compose plugin) and git. Nothing else —
no Python, no Node, no database server. There is no VPS yet; everything runs locally.

```bash
git clone https://github.com/ahll19/lauridsen-fotos.git
cd lauridsen-fotos

cp .env.example .env      # every port, path, schedule and secret lives here
scripts/install-hooks.sh  # once per clone — see below for why
scripts/dev.sh up         # build, start, and wait until the site answers
scripts/dev.sh seed       # fill it with demo content and two client galleries
scripts/dev.sh superuser  # create your admin login, interactively
```

The first build takes a few minutes; after that a cold start is about ten seconds.

**`.env` is never committed.** It is in `.gitignore`, `scripts/verify.sh` fails if it ever
gets tracked, and `.env.example` documents every value it can hold. The defaults are for local
use only — the secret key in there is a placeholder, and the application refuses to start with
it once `DJANGO_DEBUG=0`.

**`install-hooks.sh` points git at `.githooks/`.** Those hooks refuse a direct push to `main`,
run the fast verification before each commit, and reject a commit message that does not parse.
They are the only enforcement there is: the repository is private on a free GitHub plan, where
GitHub cannot enforce branch protection server-side ([ADR 0001](docs/decisions/0001-local-enforcement-of-main-protection.md)).
Run it once per clone. Never bypass a hook with `--no-verify`.

---

## Everyday commands

Everything routine is a script, so nothing lives only in your shell history.

### `scripts/dev.sh` — the local stack

| Command | What it does |
| --- | --- |
| `dev.sh up` | Builds if needed, starts everything, waits until the site answers, prints the URLs. Safe to run repeatedly. |
| `dev.sh down` | Stops the containers. Your data and photographs stay. |
| `dev.sh reset` | **Destructive.** Stops everything and deletes `./data` — database, photographs, the lot. Asks you to type `yes`. |
| `dev.sh logs [service]` | Follows the logs. `dev.sh logs app` for the application alone. |
| `dev.sh manage <command>` | Any Django management command, e.g. `dev.sh manage migrate`. |
| `dev.sh seed` | Creates demo content: 3 categories, 5 albums, 3 timeline entries, an active client gallery and an expired one. Clears previous demo content first. |
| `dev.sh superuser` | Creates an admin account, interactively. |
| `dev.sh shell` | A bash shell inside the app container. |
| `dev.sh cron` | Runs both scheduled jobs once, now, instead of waiting for their schedule. |
| `dev.sh urls` | Prints where everything is. |

### The other scripts

| Script | What it does |
| --- | --- |
| `scripts/verify.sh` | The verification pipeline: hygiene, secret scan, shell lint, Python format/lint, Django checks, migrations, tests, compose validation. Run it before opening a pull request. |
| `scripts/verify.sh --fast` | Hygiene, secrets and lint only — what the pre-commit hook runs. |
| `scripts/install-hooks.sh` | Points git at `.githooks/`. Once per clone. |
| `scripts/new-branch.sh <type> <slug>` | Creates a correctly named branch off an up-to-date `main`. The slug must be lowercase words separated by single hyphens. |
| `scripts/release.sh prepare <major\|minor\|patch>` | Bumps `VERSION`, writes the changelog, opens a release pull request. |
| `scripts/release.sh tag` | Run on `main` after that pull request merges. Creates and pushes the annotated tag. |

Checks that have nothing to verify yet are **skipped loudly** rather than silently passing, so
`verify.sh` works from an empty repository through to a finished one. `ruff` and `shellcheck`
are optional locally; CI always runs them.

---

## Running the site

`scripts/dev.sh urls` prints these. With the default `.env`:

| | |
| --- | --- |
| Site | http://localhost:8080/ |
| Admin | http://localhost:8080/studio-admin/ |
| Mail | http://localhost:8025/ — **every message the site sends is caught here**, nothing leaves your machine |
| Health | http://localhost:8080/healthz |

The admin path is not `/admin/`. It comes from `DJANGO_ADMIN_PATH` and is a shared secret in
production, on top of the account password.

The site is bilingual. Danish is the default and has no prefix; English lives under `/en/`.
**The URL decides the language**, not a cookie — so a link you send always opens in the
language you sent.

---

## Publishing: the things you do most

All of this is in the admin. You never touch code to publish anything.

### A new portfolio album

1. **Portfolio → Albummer → Tilføj album.**
2. Pick its **kategori**, give it a **navn**, and a **kort-navn** (the slug — this becomes part
   of the URL, so keep it lowercase and hyphenated).
3. Use the **Add photographs** field to select as many files at once as you like.
4. Leave **synlig** unticked while you work. Tick it when the album is ready to be public.
5. Save. Drag the photographs into the order you want, and set a **forsidebillede** if you do
   not want the first photograph used as the cover.

An album is only visible publicly if **both** it and its category are ticked **synlig**. That
is deliberate: it lets you prepare a whole category in private.

### A timeline entry

**Timeline → Tidslinjeindlæg → Tilføj.** Title, date, a short story, a photo set, optional
comma-separated tags. Same **synlig** rule. The timeline is reverse-chronological by date.

### Page text, prices and contact details

These are **singletons** — one row each, so there is nothing to add, only to edit:

- **Sider → Forside** — hero image, business name, tagline, introduction, and whether to show
  a featured album and the latest timeline entry.
- **Sider → Om-side** — portrait, heading, biography, "how I work".
- **Sider → Kontaktside** — public email, phone, Instagram and Facebook URLs.
- **Sider → Prisside** plus **Prispakker** — the packages themselves: name, inclusions (one per
  line), price as free text so you keep control of wording like "fra 4.500 kr.".

Each package's **Forespørg** button links to the contact form with the package name already
filled in, so an enquiry tells you which package prompted it.

### Writing in both languages

Any translatable field shows Danish and English side by side in the admin. Fill in Danish
first — if English is left empty, the site falls back to Danish rather than showing an empty
page, so a half-translated site still works. Shipping visible Danish on the English site is a
rough edge, not a crash.

---

## Client galleries, start to finish

This is the part with real consequences, so it is worth knowing exactly how it behaves.

### Creating one

1. **Klientgallerier → Tilføj klientgalleri.**
2. **Etiket** is your own reference — "Sofie & Jonas, bryllup i juni". The client never sees it.
3. **Klientnavn** is shown to the client as a greeting. Optional.
4. **Udløber** defaults to 90 days out (`GALLERY_DEFAULT_EXPIRY_DAYS`). Change it per gallery.
5. Upload the photographs with **Add photographs**.
6. Save.

On save the admin shows the **password once, in a yellow banner**. It is hashed immediately and
cannot be recovered — copy it now. If you lose it, use the **Generer ny adgangskode** action,
which issues a new one and shows it once.

7. Select the gallery and run the **Byg download-ZIP igen** action. Until you do, the client can
   download photographs individually but the download-all button has nothing behind it.
8. Send the client the link (shown as **klientlink**) and the password, separately if you like.

### What the client sees

An unguessable URL plus a password. Before unlocking, the page shows nothing at all — no
thumbnails, no filenames, not even how many photographs there are. After unlocking, they get
the full set, individual downloads, a download-all ZIP named after them rather than the URL
key, and a visible note saying when the gallery expires.

The unlock lasts 24 hours (`GALLERY_SESSION_MAX_AGE`) and is scoped to that one gallery.

### Expiry, which is automatic

On the expiry date, a scheduled job **deletes the photographs from disk** — originals,
derivatives and the ZIP. The gallery's URL keeps answering for another 30 days
(`GALLERY_TOMBSTONE_RETENTION_DAYS`) with a "no longer available" notice, so a client arriving
late gets an explanation instead of a dead link. After that the row is deleted too.

This is a data-retention promise, not just a UI state: the bytes really do leave the disk.

### Managing one mid-flight

Admin actions, on selected galleries:

| Action | Effect |
| --- | --- |
| **Byg download-ZIP igen** | Rebuilds the download-all archive. Run it after adding photographs. |
| **Generer ny adgangskode** | New password, shown once. |
| **Forlæng med 30 dage** | Pushes the expiry date out. |
| **Luk nu (sletter billederne)** | Expires it immediately and deletes the files. Not reversible. |

Deleting a gallery outright — single or in bulk — removes its photographs from disk too.

---

## Changing how it is configured

**Nothing operational is hardcoded.** Ports, schedules, retention windows, the admin path,
upload limits and cache policy all come from `.env`, and `.env.example` documents every one.

```bash
# edit .env, then:
scripts/dev.sh down && scripts/dev.sh up
```

Things you might reasonably change:

| Variable | What it controls |
| --- | --- |
| `HTTP_PORT` | The port the site listens on. Change it if 8080 is taken. |
| `DJANGO_ADMIN_PATH` | Where the admin lives. |
| `CRON_SCHEDULE_EXPIRE_GALLERIES` | When expired galleries are deleted. Standard five-field cron. |
| `CRON_SCHEDULE_PURGE_TOMBSTONES` | When the "no longer available" notice is finally removed. |
| `GALLERY_DEFAULT_EXPIRY_DAYS` | Default lifetime of a new gallery. |
| `GALLERY_TOMBSTONE_RETENTION_DAYS` | How long the notice survives past expiry. |
| `CONTACT_RATELIMIT` | Contact form submissions allowed per sender. |
| `MAX_UPLOAD_SIZE` | Largest upload nginx will accept. |
| `STATIC_CACHE_CONTROL` | How browsers cache CSS and JS. See the note in `.env.example` before touching this. |

**Quote any value containing a space or an asterisk** — `"0 3 * * *"`, not `0 3 * * *`. The
scripts read `.env` with the shell, so an unquoted cron expression is parsed as a command.

If you add a new value with an operational knob, it gets an environment variable with a
sensible default, documented in `.env.example` — not a literal in the code.

---

## Working on the code

### The rules, briefly

`main` is protected and is never committed or pushed to directly. Every change starts on a
branch, and reaches `main` through a pull request:

```bash
scripts/new-branch.sh fix thumbnail-orientation
# ... work, commit ...
scripts/verify.sh
git push -u origin fix/thumbnail-orientation
# then open the pull request yourself, on GitHub
```

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) —
`fix(gallery): honour EXIF orientation when resizing`. The `commit-msg` hook rejects anything
that does not parse, because `release.sh` derives version numbers and the changelog from them.

The full rules are in [CLAUDE.md](CLAUDE.md), including the list of things never to do.

### Running the tests

```bash
scripts/dev.sh manage test              # the whole suite
scripts/dev.sh manage test galleries    # one app
scripts/verify.sh                       # everything CI runs
```

Tests get their own throwaway data directory, so running them never touches your photographs.

### Changing how it looks

Everything visual is `src/static/css/site.css`, and the palette is CSS custom properties at
the top of it. Changing the accent colour is two values. There is no build step — edit the
file and reload.

The direction is **Atelier Sage**, recorded in [ADR 0003](docs/decisions/0003-visual-direction-atelier-sage.md).
Note that errors deliberately do **not** use the accent: with a green accent an error message
would sit beside a green success message and stop reading as a warning, so errors have their
own token.

Templates are in `src/templates/`, organised by app. Multi-line template comments must use
`{% comment %}`, not `{# … #}` — Django's `{# #}` is single-line only, and a multi-line one
renders into the page as visible text.

### Changing interface text

Interface strings live in `src/locale/da/LC_MESSAGES/django.po`. After changing or adding a
translatable string in code:

```bash
scripts/dev.sh manage makemessages -l da --no-location --no-wrap
# edit django.po, filling in every empty msgstr
scripts/dev.sh manage compilemessages
docker compose restart app
```

Watch for entries marked `#, fuzzy` — gettext **ignores** them at runtime, so a fuzzy entry
renders in English even though it looks translated. Fix the text and delete the fuzzy line.

Content text — album names, prices, your biography — is not here. That is in the admin.

---

## Cutting a release

The version lives in `VERSION` and follows [SemVer](https://semver.org/). `0.x` is pre-launch;
`1.0.0` is cut when the site first goes live on the VPS.

- **patch** — bug fixes, content changes, dependency bumps.
- **minor** — new functionality that does not change how the site is deployed or operated.
- **major** — anything needing a deliberate operational change on the host.

Two steps, because `main` cannot be pushed to directly:

```bash
scripts/release.sh prepare minor   # bumps VERSION, writes CHANGELOG, opens a pull request
#   ... review and merge that pull request on GitHub ...
scripts/release.sh tag             # on main, afterwards: creates and pushes the tag
```

Tags are the only thing ever pushed straight to the remote without a pull request.

---

## When something is wrong

**The site looks unstyled, or shows an old design.**
Hard-reload (`Cmd-Shift-R`). Browsers cache CSS, and in development the filename has no content
hash to force a re-fetch.

**`scripts/dev.sh` prints `line NN: command not found`.**
A value in `.env` contains a space or an asterisk and is not quoted. Quote it.

**A port is already in use.**
Change `HTTP_PORT` (or `MAIL_UI_PORT`) in `.env` and restart.

**`docker` commands hang with no output.**
Usually the Docker Desktop credential helper. Restart Docker Desktop.

**The site will not come up.**
`dev.sh up` prints the last 40 log lines on failure. Otherwise `dev.sh logs app`. The most
common cause after a code change is a migration that has not run — `dev.sh manage migrate`.

**A photograph 404s after you moved an album between categories.**
Uploads are stored under a path built from the category and album slug at upload time, and
renaming does not move the files. Re-upload the photographs.

**You lost a client gallery password.**
It cannot be recovered — only hashes are stored. Use **Generer ny adgangskode** and send the
client the new one.

**Something in the admin is in English.**
A translatable string was added without a catalogue entry, or its entry is marked fuzzy. See
[Changing interface text](#changing-interface-text).

---

## How it is laid out

```
docker/          Dockerfile, entrypoint, nginx template, cron table template
src/             the Django project
  config/        settings, URLs, WSGI, the test runner
  core/          shared plumbing: sitemap, health check, proxy middleware, upload field
  portfolio/     Category → Album → Photo
  timeline/      showcase sessions
  pages/         home/about/contact/pricing singletons, packages, contact submissions
  galleries/     private client galleries: password gate, expiry, ZIP delivery
  templates/     server-rendered HTML
  static/        hand-written CSS, small vanilla JS, vendored lightbox
  locale/        Danish interface strings
scripts/         dev, verify, release, hooks, branch creation
docs/decisions/  decision records
docs/defects.md  known defects, with severity and status
```

Four containers: **reverse-proxy** (nginx — serves static files and thumbnails, proxies the
rest), **app** (gunicorn and Django), **app-cron** (the scheduled jobs), and **mail-relay**
(Mailpit locally, a send-only Postfix in production).

Persistent data lives in one bind-mounted directory — `./data` locally, `/data` in the
containers — holding the SQLite database, uploaded originals, and a disposable thumbnail cache
that backups skip. One directory is the whole of the state, which is what makes backup a single
`rsync`.

Host management will live in `ansible/` — provisioning, deployment, updates and backup/restore
as playbooks, so the VPS is reproducible rather than hand-built. See [ROADMAP.md](ROADMAP.md)
0.4.0.

---

## The design documents

Three documents describe the whole system, and they are the source of truth for what gets
built. Read them in order:

| Document | Covers |
| --- | --- |
| [functional_design.md](functional_design.md) | What the site does, page by page. No technology choices. |
| [architecture.md](architecture.md) | How the hosting environment is built and operated. |
| [technical_design.md](technical_design.md) | How the application implements the functional design. |

[ROADMAP.md](ROADMAP.md) tracks what stands between here and 1.0.0, with a definition of done
for each milestone. [CHANGELOG.md](CHANGELOG.md) records what has changed.
[docs/decisions/](docs/decisions/) holds the decision records — the choices that would surprise
someone who had read only the design documents.

[CLAUDE.md](CLAUDE.md) has the working rules: branching, commit convention, versioning,
verification, and what never to do.
