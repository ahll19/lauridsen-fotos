# 0007. The host pulls releases from the public repository

- **Date**: 2026-11-12
- **Status**: Accepted
- **Affects**: `architecture.md` §10. Supersedes [0005](0005-ship-releases-from-the-operators-machine.md)

## Context

[ADR 0005](0005-ship-releases-from-the-operators-machine.md) had the operator's machine
pack each release and copy it to the host, for one reason: the repository was private, and
pulling would have put a GitHub credential on a machine that faces the internet.

The repository is being made public. A public repository is read without a credential, so
that reason is gone, and what `architecture.md` §10 described in the first place — the host
pulls — is the simpler arrangement.

## Decision

The host fetches from `app_repo_url` into a bare copy at `/opt/lauridsen-fotos/repo.git`
and unpacks the commit named by `deploy_ref` into a release directory named after it.
`deploy_ref` is a branch, tag or commit and defaults to `main`. The image is still built on
the host.

The host holds no credential for the repository. If the repository is private, the deploy
fails at the fetch.

The rest of ADR 0005 stands: a release directory is exactly one commit, each deploy
recreates the proxy and the application together, and rolling back is deploying an earlier
revision.

## Consequences

Only what has been pushed can be deployed. That is the point for production — the server
runs what is on GitHub, not what happens to be on a laptop — but it means a deploy no longer
picks up the commit that is checked out. `scripts/ansible.sh deploy` deploys `main`.

A rehearsal has to work before a push, so `scripts/vm.sh` copies the checkout's commits to
the disposable machine as a git bundle and points `app_repo_url` at that. The host runs the
same fetch either way.

A deploy depends on GitHub being reachable from the host. If it is not, nothing changes on
the host and the site keeps running the release it has.

Going back to a private repository would mean going back to ADR 0005, or giving the host a
read-only deploy key.
