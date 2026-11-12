# 0005. Ship releases from the operator's machine rather than pulling on the host

- **Date**: 2026-11-11
- **Status**: Superseded by [0007](0007-the-host-pulls-releases-from-the-public-repository.md)
- **Affects**: `architecture.md` §10, which says the host runs `git pull`

## Context

`architecture.md` §10 describes deployment as `git pull` and `docker build` on the VPS. The
repository is private, so for the host to pull it would need a credential for GitHub: a
deploy key generated, stored in the vault, added to the repository by hand, and kept on a
machine that faces the internet.

## Decision

`deploy.yml` packs the committed tree at a chosen revision with `git archive` on the machine
running the playbook, and unpacks it on the host as a release directory named after the
commit. The image is still built on the host, as the architecture says. The host never
talks to GitHub and holds no credential for it.

What is deployed is exactly a commit: uncommitted edits in the working tree are not in the
archive and cannot reach the server.

## Consequences

A deploy needs a checkout on the operator's machine, which it already needed for the
playbooks and the vault. Moving to CI later is unchanged from what §10 anticipated — the CI
job has a checkout too, and calls the same playbook.

Each release has its own directory, so the reverse proxy and the application are recreated
on every deploy even when only one changed. That costs a few seconds of downtime per deploy
and buys never serving a new application through an old proxy configuration. The mail
relay mounts nothing from the release and is left running.

Rolling back is deploying the earlier revision: `scripts/ansible.sh deploy -e deploy_ref=<tag>`.
