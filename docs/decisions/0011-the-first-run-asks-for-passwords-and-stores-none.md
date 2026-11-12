# 0011. The first run asks for passwords and stores none

- **Date**: 2026-11-12
- **Status**: Accepted
- **Affects**: architecture.md §11; supersedes [0010](0010-ssh-accepts-the-operators-password.md)

## Context

ADR 0010 kept the operator's password in the vault and left sshd accepting passwords. The
first run against the real server showed two things wrong with that.

It did not work: the server was installed with a root password, so its first account is not
in sudoers, and the operator's password could not get the playbooks to root.

And it was more than is wanted. A password is only needed once, to get onto a server that
does not have the operator's key yet. Keeping it in the vault, and keeping password logins
on, makes a one-time need permanent.

## Decision

The operator is still an account that already exists on the server, named in the vault
(`vault_operator_user`), and the role still never changes an existing account's password.

No password is stored. `scripts/ansible.sh provision --first-run` asks for two: the
operator's, to log in over SSH, and root's, to become root with `su`. They are used for that
run and kept nowhere.

That run installs the operator's key and passwordless sudo rule and switches password logins
off. architecture.md §11 holds again: SSH is key-only. Every later run logs in with the key
and asks for nothing.

## Consequences

The first run needs `sshpass` on the machine running the playbooks, and someone at the
keyboard who knows both passwords.

`--first-run` uses `su` because that works on a host installed with a root password. On a
host where the first account is in sudoers and root has no password, add
`--become-method sudo` after it and give the operator's password twice.

If the key is ever lost there is no password login to fall back on: the way back in is the
server's console.
