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
- Three alternative visual directions — Darkroom, Broadsheet and Nordic — alongside the
  existing one, switchable on the real site so they can be judged on real content rather
  than mockups. A comparison page lives at `/design/`. The whole preview is gated behind
  `DESIGN_PREVIEW_ENABLED`, which is off outside development, and goes away once a
  direction is chosen (ROADMAP 0.2.0).
- Ansible is now the way the remote host is managed: an `ansible/` directory with the
  environment and playbooks for provisioning, deployment, updates and backup/restore, so the
  server is rebuilt from a clone rather than from memory. Recorded in ADR 0002 and reflected
  in `architecture.md` §2, §10 and §11; `scripts/verify.sh` already lints it and refuses an
  unencrypted vault file.

### Fixed

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
