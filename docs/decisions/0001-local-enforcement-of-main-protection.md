# 0001. Enforce main protection locally rather than on GitHub

- **Date**: 2026-09-12
- **Status**: Accepted
- **Affects**: none of the design documents; this concerns the development workflow only

## Context

The project requires that `main` be protected: no direct pushes, and changes reaching it only
through a pull request that has passed verification.

GitHub cannot provide this here. Both classic branch protection rules and the newer rulesets
are available on **public** repositories under the Free plan, but on **private** repositories
they require GitHub Pro or above. This repository is private, and paying for Pro was
considered and declined. Making the repository public would have restored server-side
enforcement for free, but was not wanted for a business site.

GitHub Actions does run on private repositories under the Free plan (2000 minutes per month),
so verification can still run automatically on every pull request — it simply cannot be marked
as a *required* check that blocks the merge button.

## Decision

Protection of `main` is enforced by a version-controlled `pre-push` hook in `.githooks/`,
installed per clone by `scripts/install-hooks.sh`. The hook refuses any push whose destination
is `refs/heads/main`, while allowing tag pushes so releases can be published.

The verification pipeline lives in `scripts/verify.sh` and is the single definition of
"verified". It runs locally via the `pre-commit` hook (fast subset) and in GitHub Actions on
every pull request (in full). The Actions result is treated as blocking by convention even
though GitHub will not enforce it.

Using `--no-verify` is forbidden by `CLAUDE.md`, since it is the one action that defeats all
of the above.

## Consequences

Enforcement is advisory rather than absolute. A push to `main` is possible for anyone who
skips hook installation or passes `--no-verify`; with a single maintainer, that risk is
accepted in exchange for keeping the repository private at no cost.

Hooks must be installed explicitly after cloning, which is a step that can be forgotten.
`scripts/install-hooks.sh` exists to make it one command, and the setup instructions in
`CLAUDE.md` name it first.

Revisiting this is cheap and requires no change to the workflow itself: subscribing to GitHub
Pro, or making the repository public, would let the same `scripts/verify.sh` become a required
status check with no edits to the script, the workflow, or the branching model. Only the
enforcement layer changes.
