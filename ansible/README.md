# Running the playbooks

Everything here is plain Ansible, run from this directory. There is no wrapper script.

```bash
cd ansible
ansible-playbook playbooks/deploy.yml -J
```

`-J` asks for the vault password. `ansible.cfg` in this directory supplies the rest: the
production inventory, the roles, and where the collections live.

## The commands

| To | Run |
| --- | --- |
| Set up a server for the first time | `ansible-playbook playbooks/provision.yml -J -k -K --become-method su` |
| Re-apply the server's configuration | `ansible-playbook playbooks/provision.yml -J` |
| Deploy `main` | `ansible-playbook playbooks/deploy.yml -J` |
| Deploy a tag or a branch | `ansible-playbook playbooks/deploy.yml -J -e deploy_ref=v1.0.0` |
| Patch the OS, refresh images, redeploy | `ansible-playbook playbooks/update.yml -J` |
| Install the nightly backup | `ansible-playbook playbooks/backup.yml -J` |
| Install it and take a copy now | `ansible-playbook playbooks/backup.yml -J -e backup_run_now=true` |
| Restore the newest backup | `ansible-playbook playbooks/restore.yml -J` |

Every playbook is safe to run again. Rolling back is deploying an earlier tag.

## Setting up a machine or a server

[Deploying to a server](../README.md#deploying-to-a-server) in the main README is the
procedure, in order: the tools to install, the inventory files to fill in, and the first
run, which is the only one that asks for passwords
([ADR 0011](../docs/decisions/0011-the-first-run-asks-for-passwords-and-stores-none.md)).

## Trusted machines

The server accepts the SSH keys listed in
`inventory/production/group_vars/all/trusted_keys.yml`, and no others. It is one public key
per machine that maintains the server.

To add the machine you are sitting at, from the repository root:

```bash
printf '  - %s\n' "$(cat ~/.ssh/id_ed25519.pub)" >> ansible/inventory/production/group_vars/all/trusted_keys.yml
```

Commit that, then run provision **from a machine that is already trusted**. A new machine
cannot let itself in. To remove a machine, delete its line and run provision.

Provision refuses to run from a machine none of whose own keys is in the list, so the
first run cannot switch password logins off and leave you outside.

## The vault password

`-J` asks every time. To be asked less, put the password in `ansible/.vault-pass`, which is
gitignored, and use `--vault-password-file .vault-pass` in place of `-J`.

`scripts/vault.sh` creates, edits and prints the vault itself.

## Rehearsing on a disposable machine

`scripts/vm.sh up` starts two throwaway Debian machines and writes
`inventory/disposable/`. Point any playbook at it with `-i`. It has no vault, so no `-J`:

```bash
ansible-playbook -i inventory/disposable playbooks/provision.yml
```

```bash
ansible-playbook -i inventory/disposable playbooks/deploy.yml
```

The rehearsal server gets the code from a copy of this checkout, not from GitHub. After a
new commit, hand it over before deploying:

```bash
scripts/vm.sh sync
```

## Where things are

| Path | Holds |
| --- | --- |
| `ansible.cfg` | Defaults: inventory, roles, collections, SSH options |
| `inventory/production/hosts.yml` | The server's address |
| `inventory/production/group_vars/all/vars.yml` | Settings specific to the real server |
| `inventory/production/group_vars/all/trusted_keys.yml` | The SSH public keys that may log in |
| `inventory/production/group_vars/all/vault.yml` | The secrets, encrypted |
| `playbooks/` | One file per command above |
| `roles/` | What each playbook applies; each role's `defaults/main.yml` lists its settings |
| `requirements.yml` | The pinned collections |
