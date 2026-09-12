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

## [0.1.0] - 2026-09-12

### Added

- Functional, architecture and technical design documents describing the whole setup.
- Project working rules in `CLAUDE.md`, workflow scripts in `scripts/`, and version-controlled
  git hooks enforcing branch protection and commit conventions locally.
