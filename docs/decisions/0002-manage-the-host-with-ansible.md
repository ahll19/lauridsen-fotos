# 0002. Manage the host with Ansible, with secrets in ansible-vault

- **Date**: 2026-09-13
- **Status**: Accepted
- **Affects**: `architecture.md` §2, §10 and §11, which have been updated to match

## Context

`architecture.md` described what the host should look like — Debian, Docker, `ufw`,
`unattended-upgrades`, SSH key-only, a `/data` bind mount — but said nothing about how it
gets into that state. Read literally, it implied someone would SSH in and configure it by
hand, once, and then remember what they did.

That is the failure mode worth avoiding. A hand-built server is a pet: the reasoning behind
its configuration lives in one person's memory, drift is invisible, and rebuilding it after a
loss, a provider change, or a botched upgrade means reconstructing it from recollection under
pressure. The design documents are unusually careful about being explicit; the host itself
should be held to the same standard.

Ansible fits the constraints already established. It is agentless, so it adds nothing to the
running host and keeps "Docker Engine and the Compose plugin are the only dependencies" true.
It needs only SSH, which is already the access path. It is declarative enough to be read as
documentation. And because `architecture.md` §10 anticipates a later move to Jenkins, having
the deployment sequence already expressed as a playbook means that move becomes "CI calls the
playbook" rather than a rewrite.

The alternative of shell scripts in `scripts/` was considered. Scripts would work, but they
describe steps rather than desired state, which makes them awkward to re-run safely and
awkward to read as a description of the server.

## Decision

Host management lives in an `ansible/` directory in this repository, applied from the
operator's machine over SSH. It covers provisioning a bare host, deploying the application,
running maintenance updates, and installing and exercising backups. No configuration step
exists outside it — if something has to be done to the host, it is a playbook, not an
instruction in a document.

Secrets the playbooks need are kept in `ansible-vault`-encrypted files committed alongside
the rest of the configuration. The vault password is never committed; it lives in the
owner's password manager. A clone of this repository plus that one password is therefore
sufficient to rebuild the server from nothing.

## Consequences

The vault password becomes a single point of failure: lose it and the encrypted values are
gone, which makes the password manager entry part of the backup story rather than an
afterthought. In exchange, disaster recovery is a clone, a vault password, and a fresh
machine — with no dependency on any other system being reachable.

Committing encrypted secrets means the ciphertext is in git history forever. If a value ever
leaks it must be rotated, not merely removed from a file, because the old ciphertext remains
in every clone. This is the accepted cost of keeping the rebuild self-contained.

Ansible becomes a prerequisite on the operator's machine. That is a small burden for one
operator, and none at all for the server.

Because the playbooks define the host, they must be kept honest: a change made by hand during
an incident has to be folded back into a playbook afterwards, or the next rebuild silently
loses it.
