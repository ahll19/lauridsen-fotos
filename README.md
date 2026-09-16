# Lauridsen Fotos

A photography portfolio and client delivery site: public albums, a photo-led timeline,
pricing and contact pages, and private client galleries that delete themselves when they
expire.

Django behind nginx on a single Docker Compose stack, in Danish and English. No build step —
server-rendered templates and hand-written CSS.

## Running it

Docker is the only requirement. There is no server yet; this all runs on your machine.

```bash
cp .env.example .env
scripts/install-hooks.sh   # once per clone
scripts/dev.sh up
scripts/dev.sh seed        # demo content, if you want something to look at
scripts/dev.sh superuser   # your admin login
```

The site is then at <http://localhost:8080/> and the admin at `/studio-admin/` — not
`/admin/`, since that path is a shared secret in production. Every email the site sends is
caught at <http://localhost:8025/> rather than delivered. `scripts/dev.sh urls` prints all
of them.

Danish is the default and has no URL prefix; English lives under `/en/`. The URL decides the
language, so a link opens in the language you sent it in.

## Publishing

Everything is managed in the admin. You never edit code to publish.

Albums live under Portfolio, inside a category. Upload as many photographs at once as you
like, drag them into order, and set a cover if you don't want the first one used. An album
is public only when both it and its category are marked *synlig*, which lets you prepare a
whole category in private. Timeline entries work the same way — a title, a date, a short
story, a photo set.

Page text and prices are single records rather than lists: one Forside, one Om-side, one
Kontaktside, plus the pricing packages. Each package's enquiry button links to the contact
form with the package name already filled in, so you know what prompted an enquiry.

Translatable fields show Danish and English side by side. Fill in Danish first — anything
left untranslated falls back to it rather than rendering an empty page.

## Client galleries

The part with real consequences, so it is worth knowing how it behaves.

Create one under Klientgallerier with a label for your own reference, the client's name, an
expiry date (90 days out by default) and the photographs. On save the admin shows the
password once. It is hashed immediately and cannot be recovered, though you can issue a new
one later. Then run the *Byg download-ZIP igen* action, or the download-all button has
nothing behind it.

Send the client the link and the password. Until they enter it the page reveals nothing — no
thumbnails, no filenames, not even how many photographs there are.

On the expiry date a scheduled job deletes the photographs from disk. The URL keeps
answering for another month with a "no longer available" notice, so a client arriving late
gets an explanation rather than a dead link, and then the record goes too. Deleting a gallery
by hand removes its files the same way.

## Configuration

Ports, schedules, expiry windows, the admin path and upload limits all come from `.env`, and
`.env.example` documents every one. Edit it, then restart:

```bash
scripts/dev.sh down && scripts/dev.sh up
```

Quote any value containing a space or an asterisk — `"0 3 * * *"` — because the scripts read
the file with the shell.

Switching the mail relay means changing three values together:

| | Mailpit, for development | Postfix, as production runs |
| --- | --- | --- |
| `COMPOSE_PROFILES` | `dev` | `prod` |
| `EMAIL_PORT` | `1025` | `587` |
| `DEFAULT_FROM_EMAIL` | anything | must be on `MAIL_SENDER_DOMAIN`, or the relay refuses it |

`DJANGO_DEBUG` and `STATIC_CACHE_CONTROL` travel together too: `immutable` is only ever a
true thing to say about a filename carrying a content hash, which is what `DJANGO_DEBUG=0`
produces. `scripts/prodcheck.sh` sets both correctly, so prefer it to changing them by hand.

## Working on the code

Branch, verify, then open a pull request:

```bash
scripts/new-branch.sh fix thumbnail-orientation
scripts/verify.sh
```

`main` is protected, commit messages follow Conventional Commits, and the git hooks enforce
both locally. [CLAUDE.md](CLAUDE.md) has the working rules in full.

Production is a different code path, not just a different flag — assets get content-hashed
names, errors become pages instead of tracebacks, and the security middleware stops being
lenient. `scripts/prodcheck.sh` runs the stack that way here and checks it, then puts
development mode back — `--keep` leaves it there if you want to click around. Worth running
before anything that touches templates, static files or settings.

The look is `src/static/css/site.css`, with the palette as custom properties at the top —
changing the accent is two values. Interface strings live in `src/locale/da/`: after touching
one, run `makemessages`, translate the new entries, then `compilemessages`. Content text is
not there; it is in the admin.

Releases happen in two steps, since `main` cannot be pushed to directly:

```bash
scripts/release.sh prepare minor   # bumps VERSION, writes the changelog, opens a pull request
scripts/release.sh tag             # on main, once that is merged
```

---

## Reference

### Scripts

`scripts/dev.sh <command>` runs the local stack:

| | |
| --- | --- |
| `up` | Build if needed, start, wait until the site answers. Safe to repeat. |
| `down` | Stop. Data and photographs stay. |
| `reset` | Stop and delete `./data` — database and every photograph. Asks for confirmation. |
| `logs [service]` | Follow the logs. |
| `manage <command>` | Any Django management command. |
| `seed` | Demo content: categories, albums, timeline entries, an active and an expired gallery. |
| `superuser` | Create an admin account. |
| `shell` | A shell inside the app container. |
| `cron` | Run both scheduled jobs once, now. |
| `urls` | Print where everything is. |

The rest:

| | |
| --- | --- |
| `scripts/verify.sh` | Hygiene, secrets, lint, Django checks, migrations, tests, compose validation. Run before a pull request; `--fast` is the subset the pre-commit hook runs. |
| `scripts/prodcheck.sh` | Runs the stack with production settings and checks it, then restores development mode. `--keep` leaves it in production mode to look around. |
| `scripts/crawl.py <url>` | Follows every link and `src` on the running site and reports anything that is not a 200. Used by `prodcheck.sh`; useful on its own after a template change. |
| `scripts/install-hooks.sh` | Points git at `.githooks/`. Once per clone. |
| `scripts/new-branch.sh <type> <slug>` | A correctly named branch off an up-to-date `main`. |
| `scripts/release.sh` | `prepare <major\|minor\|patch>` then `tag`. |

Checks with nothing to verify yet are skipped loudly rather than passing silently.

### Layout

```
docker/          Dockerfile, entrypoint, nginx and cron templates
src/
  config/        settings, URLs, WSGI, test runner
  core/          sitemap, health check, proxy middleware, upload field
  portfolio/     Category → Album → Photo
  timeline/      showcase sessions
  pages/         home/about/contact/pricing, packages, contact submissions
  galleries/     password gate, expiry, ZIP delivery
  templates/ static/ locale/
scripts/         dev, verify, release, hooks, branch creation
docs/            decision records, defect register
```

Four containers: nginx, the application, a cron container for the scheduled jobs, and a mail
relay. All state lives in one bind-mounted directory — `./data` here, `/data` in the
containers — holding the database, the uploaded originals, and a disposable thumbnail cache
that backups skip.

The relay is two services rather than one: Mailpit captures mail and shows it in a browser,
Postfix delivers it straight to recipients
([ADR 0004](docs/decisions/0004-deliver-mail-directly-rather-than-through-a-smarthost.md)).
Both answer to the name `mail-relay`, so the application never knows which is running.

### When something is wrong

- **Old styling after a change** — hard-reload. In development the filenames carry no
  content hash to force a re-fetch.
- **`command not found` from a script** — an unquoted value in `.env`.
- **Port already in use** — change `HTTP_PORT` in `.env`.
- **Docker hangs with no output** — usually the Docker Desktop credential helper. Restart it.
- **The site will not start** — `dev.sh up` prints the last log lines on failure; after a
  code change the usual cause is a pending migration.
- **A photograph 404s after moving an album** — upload paths are built from the slugs at
  upload time and renaming does not move files. Re-upload them.
- **Every request redirects to `https://` and nothing answers** — production settings without
  a certificate in front. Set `DJANGO_SERVE_OVER_HTTPS=0`, or use `prodcheck.sh`, which does.
- **Mail disappears with no error** — either `COMPOSE_PROFILES` names a relay that is not
  running, or Postfix is running and `DEFAULT_FROM_EMAIL` is not on `MAIL_SENDER_DOMAIN`.

### Documents

[functional_design.md](functional_design.md) covers what the site does, page by page;
[architecture.md](architecture.md) how the hosting environment is built and operated;
[technical_design.md](technical_design.md) how the application implements it. These three are
the source of truth for what gets built.

[ROADMAP.md](ROADMAP.md) tracks what stands between here and 1.0.0.
[CHANGELOG.md](CHANGELOG.md) records what has changed. [docs/decisions/](docs/decisions/)
holds the choices that would surprise someone who had read only the design documents, and
[docs/defects.md](docs/defects.md) the known defects.
