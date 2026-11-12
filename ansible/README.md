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

## Once per machine

```bash
brew install ansible sshpass
```

```bash
cd ansible && ansible-galaxy collection install -r requirements.yml
```

The second installs the pinned collections into `ansible/.collections`. Run it again with
`--force` after `requirements.yml` changes. `sshpass` is only needed for the first run on a
new server.

## The first run on a new server

A new server does not have your SSH key yet, so one run logs in with passwords:

```bash
ansible-playbook playbooks/provision.yml -J -k -K --become-method su
```

It asks three things, and stores none of them:

| Prompt | Give it |
| --- | --- |
| `SSH password` | your account's password on the server |
| `BECOME password` | root's password on the server |
| `Vault password` | the vault password |

That run installs your key, lets your account use sudo, and switches password logins off.
From then on the server accepts only the key, and no command needs `-k`, `-K` or
`--become-method` ([ADR 0011](../docs/decisions/0011-the-first-run-asks-for-passwords-and-stores-none.md)).

`--become-method su` is for a server installed with a root password, where your account is
not in sudoers. If your account can already use sudo, leave it out and give your own
password at both prompts.

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
| `inventory/production/group_vars/all/vault.yml` | The secrets, encrypted |
| `playbooks/` | One file per command above |
| `roles/` | What each playbook applies; each role's `defaults/main.yml` lists its settings |
| `requirements.yml` | The pinned collections |
