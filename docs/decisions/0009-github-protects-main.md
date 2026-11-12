# 0009. GitHub protects main

- **Date**: 2026-11-12
- **Status**: Accepted
- **Affects**: none of the design documents. Supersedes [0001](0001-local-enforcement-of-main-protection.md)

## Context

[ADR 0001](0001-local-enforcement-of-main-protection.md) enforced the protection of `main`
with a local `pre-push` hook, because GitHub's branch protection is not available to private
repositories on the free plan. The repository is now public, and protection is free.

## Decision

GitHub protects `main` with a branch protection rule:

- every change arrives through a pull request,
- the `verify` check must pass before it can be merged,
- the rule applies to administrators too,
- `main` cannot be force-pushed or deleted.

No approving review is required. With one maintainer there is nobody else to approve, and
GitHub does not let an author approve their own pull request.

The `pre-push` hook stays. It is no longer the enforcement, but it refuses a push to `main`
on the laptop, before the network, with a message that says what to do instead.

Tags are not covered by the rule, so `scripts/release.sh tag` still pushes them directly.

## Consequences

A red `verify` now blocks the merge button rather than relying on discipline, and
`--no-verify` can no longer get anything onto `main`.

A failure in GitHub Actions itself, such as the runner losing DNS mid-install, blocks every
merge until the job is re-run. Re-running is the fix; turning the rule off is not.

Making the repository private again would lose this on the free plan and return to ADR 0001.
