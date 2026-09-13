# Working rules for this project

These rules apply to every change made in this repository, by a human or by Claude. They
exist so the project stays reviewable and releasable by one person over a long time, without
depending on anyone remembering the conventions.

## The project

A photography portfolio and client delivery site. The design is fixed in three documents and
they are the source of truth for *what* gets built:

| Document | Covers |
| --- | --- |
| [functional_design.md](functional_design.md) | What the site does, page by page. No technology choices. |
| [architecture.md](architecture.md) | How the hosting environment is built and operated. |
| [technical_design.md](technical_design.md) | How the application implements the functional design. |
| [ROADMAP.md](ROADMAP.md) | Milestones to 1.0.0, each with a definition of done. |

**Current phase: local development only.** The VPS has not been ordered yet. Everything must
run on a laptop via Docker Compose. Do not write anything that assumes a provisioned server,
a real domain, a public IP, or live TLS certificates — those arrive later, and the setup
described in `architecture.md` is the target, not the present state. `certbot` is therefore
absent from the compose file; it joins when there is a domain to point at it.

## Nothing operational is hardcoded

Ports, schedules, retention windows, paths, the admin URL and the mail relay image all come
from `.env`, and `.env.example` documents every one. When adding something with an
operational knob — a new scheduled job, a timeout, a limit — it gets an environment variable
with a sensible default, documented in `.env.example`, rather than a literal in the code, the
Dockerfile, or the compose file. The nginx config is an envsubst template and the cron table
is rendered from the environment at container start for the same reason.

## Branching

`main` is protected. Nothing is ever committed or pushed directly to it.

- Every change starts on a branch off the latest `main`.
- Branch names are `<type>/<short-slug>`, using the same types as commit messages:
  `feat/client-gallery-expiry`, `fix/thumbnail-orientation`, `docs/deployment-notes`.
- Create branches with `scripts/new-branch.sh <type> <slug>` so the name is valid by
  construction.
- Branches merge into `main` through a pull request, never by a local fast-forward.
- Delete the branch after the PR merges.

This repository is private on a free GitHub plan, which means GitHub itself **cannot** enforce
branch protection (see [docs/decisions/0001-local-enforcement-of-main-protection.md](docs/decisions/0001-local-enforcement-of-main-protection.md)).
Enforcement is a local `pre-push` hook instead. Install it once per clone:

```bash
scripts/install-hooks.sh
```

Never bypass a hook with `--no-verify`. If a hook is wrong, fix the hook in its own PR.

## Commits

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/):

```
<type>(<optional scope>): <subject>

<optional body explaining why, not what>
```

Types: `feat`, `fix`, `docs`, `style`, `refactor`, `perf`, `test`, `build`, `ci`, `chore`,
`revert`. Append `!` after the type (`feat!:`) for a breaking change — meaning one that
changes how the site is deployed, configured, or operated, not merely how it looks.

The subject is imperative and lowercase (`add gallery expiry command`, not
`Added gallery expiry command`), under 72 characters. The `commit-msg` hook rejects anything
that doesn't parse, because the release script derives version numbers and the changelog from
these messages.

Commits made by Claude end with:

```
Co-Authored-By: Claude Opus 5 <noreply@anthropic.com>
```

## Versioning and releases

The repository uses [SemVer](https://semver.org/). `VERSION` at the repo root holds the
current version and is the single source of truth. `0.x` means pre-launch; `1.0.0` is cut when
the site first goes live on the VPS.

- **patch** — bug fixes, content-only changes, dependency bumps.
- **minor** — new functionality that doesn't change how the site is deployed or operated.
- **major** — anything requiring a deliberate operational change on the host (new service,
  new required environment variable, a migration that isn't reversible, a changed data layout).

Releases happen in two steps, because `main` cannot be pushed to directly:

```bash
scripts/release.sh prepare minor   # on any branch: bumps VERSION, writes CHANGELOG, opens a PR
# ... review and merge that PR on GitHub ...
scripts/release.sh tag             # on main, after the merge: creates and pushes the tag
```

Every release is tagged `vX.Y.Z` as an annotated tag. Tags are the only thing ever pushed
straight to the remote without a PR.

## Scripts

Anything done more than twice belongs in `scripts/`, not in a README instruction or in
someone's shell history.

| Script | Purpose |
| --- | --- |
| `scripts/dev.sh` | The local stack: `up`, `down`, `reset`, `logs`, `manage`, `seed`, `superuser`, `shell`, `cron`, `urls`. |
| `scripts/verify.sh` | The verification pipeline. Run it before opening a PR. |
| `scripts/install-hooks.sh` | Points git at `.githooks/`. Run once per clone. |
| `scripts/new-branch.sh` | Creates a correctly named branch off an up-to-date `main`. |
| `scripts/release.sh` | Prepares and tags releases. |

Scripts are POSIX-ish bash, `set -euo pipefail`, and must be safe to run twice. Each one
prints what it is doing and exits non-zero on failure.

## Verification

`scripts/verify.sh` is the gate. It checks repository hygiene, scans for committed secrets,
lints shell scripts, and — once they exist — checks Python formatting and linting, runs Django's
own system checks, runs the test suite, and validates the Docker Compose file. Checks for
things that don't exist yet are skipped, loudly, so the same script works from an empty repo
through to a finished one.

```bash
scripts/verify.sh          # everything
scripts/verify.sh --fast   # hygiene, secrets, lint — what the pre-commit hook runs
```

The same script runs in GitHub Actions on every pull request. Because the repository is
private on a free plan, that result is **advisory** — GitHub will not block the merge button.
Treat a red check as blocking anyway; that discipline is the only thing standing in for
server-side enforcement.

## Decision records

The three design documents describe the agreed design. When a decision during implementation
extends or contradicts them, record it in `docs/decisions/` as a short numbered note rather
than quietly editing a design document:

```bash
cp docs/decisions/template.md docs/decisions/0002-short-slug.md
```

A decision record is warranted when a choice would be surprising to someone reading only the
design docs, or when it closes off an option those docs left open. Routine implementation
choices do not need one. When a record supersedes part of a design document, say so in the
record and add a pointer in the design document to it.

## Never

- Push or commit to `main` directly.
- Use `--no-verify`.
- Commit `.env`, credentials, certificates, or client photographs. `/data` is bind-mounted at
  runtime and is not in version control.
- Commit generated artifacts: thumbnails, `staticfiles/`, the SQLite database.
- Introduce a JavaScript build pipeline, bundler, or Node dependency. The frontend is
  server-rendered templates, hand-written CSS, and small amounts of vanilla JS, as
  `technical_design.md` specifies.
