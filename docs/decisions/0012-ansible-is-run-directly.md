# 0012. Ansible is run directly, not through a wrapper script

- **Date**: 2026-11-12
- **Status**: Accepted
- **Affects**: CLAUDE.md (Scripts); earlier records that name `scripts/ansible.sh`

## Context

The playbooks were run through `scripts/ansible.sh`, which changed directory, installed the
collections, found the vault password and, later, grew its own `--first-run` flag. The
project's rule is that anything done more than twice belongs in a script.

In use it got in the way. It had its own flags on top of Ansible's, so knowing Ansible was
not enough to run or debug it, and an error could come from either layer. The first run
against the real server failed inside the wrapper before Ansible ran at all.

## Decision

The playbooks are run with plain `ansible-playbook` from `ansible/`, and
[ansible/README.md](../../ansible/README.md) documents each command. `scripts/ansible.sh` is
removed.

What the wrapper decided is now configuration or documentation: `ansible.cfg` holds the
defaults, and the README lists the flags for the vault password and for the first run.

`scripts/vault.sh` and `scripts/vm.sh` stay. They do work Ansible has no command for:
generating the secrets, and building the rehearsal machines.

## Consequences

Anyone who knows Ansible can run the playbooks, and every flag is one the Ansible
documentation explains.

The commands are longer, and three things the wrapper did silently are now the operator's
to do: run from `ansible/`, install the collections once, and run `scripts/vm.sh sync`
before a rehearsal deploy.

Earlier records (0005, 0007, 0010) name `scripts/ansible.sh`. They are left as written;
read `ansible-playbook playbooks/<name>.yml` in its place.
