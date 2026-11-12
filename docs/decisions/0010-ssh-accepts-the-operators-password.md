# 0010. SSH accepts the operator's password, and the operator is an existing account

- **Date**: 2026-11-12
- **Status**: Superseded by [0011](0011-the-first-run-asks-for-passwords-and-stores-none.md)
- **Affects**: architecture.md §11

## Context

architecture.md §11 says SSH is key-only, and the playbooks were written for a fresh cloud
server: they log in as root once, create a `deploy` account with a locked password, install
a key for it and switch password logins off.

The server is not that. It sits on a local network that only the local network can reach,
and it already has its owner's own account, which logs in with a password. Locking that
account's password, or switching password logins off, would take away the way its owner
gets in today.

## Decision

The operator is an account that already exists on the server. Its name and password live in
the vault (`vault_operator_user`, `vault_operator_password`), and the playbooks log in with
them: SSH by password or key, sudo by password until provision installs the passwordless
sudo rule.

sshd accepts passwords when `ssh_password_authentication` is true, which the production
inventory sets. The role's default stays false, so a host without that network in front is
still key-only.

The role never changes the password of an account that already exists. It still locks the
password of an account it creates itself.

## Consequences

The server is as safe as its password and the network in front of it. If the server is ever
reachable from outside the local network, set `ssh_password_authentication: false` first and
check that the key logs in.

Logging in by password from Ansible needs `sshpass` on the machine running the playbooks.
`scripts/ansible.sh` refuses to start without it rather than failing partway through.

The operator's key is still installed, and is still the sole entry in that account's
`authorized_keys`: any other key already there is removed.
