# Lauridsen Fotos

Photography portfolio and client delivery site: a public portfolio, a photo-led timeline,
static pricing/contact/about pages, and private client galleries that delete themselves when
they expire.

Django 5.2 on Python 3.12, behind nginx, on a single Docker Compose stack. No JavaScript build
step, no framework — server-rendered templates, hand-written CSS, and one small lightbox
library.

## Running it locally

Requires Docker. There is no VPS yet; everything runs on your machine.

```bash
cp .env.example .env      # every port, path and schedule lives here
scripts/install-hooks.sh  # once per clone
scripts/dev.sh up         # build, start, wait until it answers
scripts/dev.sh seed       # fill the site with demo content and a client gallery
scripts/dev.sh superuser  # create your admin login
```

`scripts/dev.sh urls` prints where everything is. By default:

| | |
| --- | --- |
| Site | http://localhost:8080/ |
| Admin | http://localhost:8080/studio-admin/ |
| Mail | http://localhost:8025/ — every message the site sends is caught here |

Other commands: `logs`, `manage <cmd>`, `shell`, `cron` (runs the scheduled jobs once), `down`,
and `reset` (deletes the database and all uploaded photographs).

## How it is laid out

```
docker/          Dockerfile, entrypoint, nginx template, cron table template
src/             the Django project
  config/        settings, URLs, WSGI
  core/          shared plumbing: sitemap, health check, multi-file upload field
  portfolio/     Category → Album → Photo
  timeline/      showcase sessions
  pages/         home/about/contact/pricing singletons, packages, contact submissions
  galleries/     private client galleries: password gate, expiry, ZIP delivery
  templates/     server-rendered HTML
  static/        hand-written CSS, small vanilla JS, vendored lightbox
  locale/        Danish interface strings
scripts/         dev, verify, release, hooks, branch creation
docs/decisions/  decision records
```

Host management will live in `ansible/` — provisioning, deployment, updates and
backup/restore as playbooks, so the VPS is reproducible rather than hand-built. See
[ROADMAP.md](ROADMAP.md) 0.4.0.

Persistent data lives in one bind-mounted directory (`./data` locally, `/data` in the
containers): the SQLite database, uploaded originals, and a disposable thumbnail cache that
backups skip.

## The design

Three documents describe the whole system, and they are the source of truth for what gets
built. Read them in order:

| Document | Covers |
| --- | --- |
| [functional_design.md](functional_design.md) | What the site does, page by page. No technology choices. |
| [architecture.md](architecture.md) | How the hosting environment is built and operated. |
| [technical_design.md](technical_design.md) | How the application implements the functional design. |

[ROADMAP.md](ROADMAP.md) tracks what stands between here and 1.0.0, with a definition of done
for each milestone.

[CLAUDE.md](CLAUDE.md) has the working rules: branching, commit convention, versioning,
verification, and what never to do.
