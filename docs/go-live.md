# Going live

The site is built and the path to production has been rehearsed on a disposable server.
What remains needs things only you have. This is that list, in the order to do it.

Each step is one command or one thing to click. If a step ever needs you to SSH in and
type something, that is a bug in a playbook — fix the playbook.

## 1. Decide and order

The server pulls the code from the public repository and holds no credential for it. If the
repository is ever made private again, deploys fail at the fetch.

1. **A server.** Hetzner Cloud, Debian 12, 4–8 GB RAM. Add your SSH public key when
   ordering, so root accepts it.
2. **A domain**, and an A record for it (and for `www`) pointing at your reverse proxy.
3. **The reverse proxy in front.** It holds the certificate and forwards to the server's
   port 80 over plain HTTP ([ADR 0008](decisions/0008-tls-ends-at-a-reverse-proxy-in-front-of-the-server.md)).
   It must pass `Host` through, set `X-Forwarded-Proto: https`, append the visitor's
   address to `X-Forwarded-For`, and allow uploads of 100 MB taking up to five minutes.
4. **Ask Hetzner to open outbound port 25.** It is closed on new accounts and opened on
   request; without it no mail leaves. This can take a day, so ask early.

## 2. Tell the playbooks

Edit three files in `ansible/inventory/production/`:

| File | Set |
| --- | --- |
| `hosts.yml` | `ansible_host` — the server's IP address |
| `group_vars/all/trusted_keys.yml` | your SSH public key — the file says how to add it |
| `group_vars/all/vars.yml` | `operator_user` — your account on the server; `site_domain`, `owner_email`, and `upstream_proxy_addresses` — the reverse proxy's address as the server sees it connect |

Then create the secrets. You will be asked to choose the vault password; put it in your
password manager straight away, because it is the only copy.

```bash
scripts/vault.sh init
```

No login password goes in the vault. The first run asks for the ones it needs
([ADR 0011](decisions/0011-the-first-run-asks-for-passwords-and-stores-none.md)).

Commit all four files and merge them to `main`. The vault is encrypted and is meant to be
committed; the others hold nothing the site's DNS does not already publish, apart from
the two email addresses.

## 3. Build the server

The playbooks are plain Ansible, run from `ansible/`.
[ansible/README.md](../ansible/README.md) has every command; these are the ones for today.
Once per machine:

```bash
brew install ansible sshpass
```

```bash
cd ansible && ansible-galaxy collection install -r requirements.yml
```

Then, still in `ansible/`:

```bash
ansible-playbook playbooks/provision.yml -J -k -K --become-method su
```

```bash
ansible-playbook playbooks/deploy.yml -J
```

The extra flags on the first command are for this one time, while the server does not have
your SSH key yet. It asks for your account's password on the server (`SSH password`), root's
(`BECOME password`) and the vault's, and keeps none of them. Once it has run, the server
accepts only your key, and provision needs only `-J`.

The first takes a bare server to a hardened one running Docker. The second has the
server pull `main` from GitHub, builds it, starts the stack and fails unless `/healthz`
answers. Both are safe to run again. Then check the whole path, proxy included: open
`https://<your domain>/healthz` in a browser.

Then create your admin account:

```bash
ssh -t <operator>@<server> 'cd /opt/lauridsen-fotos/current && sudo docker compose exec app python manage.py createsuperuser'
```

The admin lives at the path in the vault — `scripts/vault.sh view` shows it.

## 4. Things outside the server

```bash
scripts/vault.sh public
```

prints two values to put elsewhere:

| What | Where |
| --- | --- |
| DKIM public key | a TXT record at `mail._domainkey.<domain>` |
| Backup public key | `authorized_keys` of the backup account on the NAS |

Also, for mail to be accepted rather than filed as spam:

| What | Where |
| --- | --- |
| SPF: `v=spf1 ip4:<server IP> -all` | a TXT record on the domain |
| Reverse DNS: `mail.<domain>` | the server's networking page in the Hetzner console |
| A record for `mail.<domain>` | pointing at the server |
| Firewall: 22, and 80 from the reverse proxy only | Hetzner Cloud Firewall, attached to the server |

## 5. Backups

Set `backup_target_host` (and user, port, path if they differ) in `vars.yml`, then:

```bash
ansible-playbook playbooks/backup.yml -J -e backup_run_now=true
```

That installs the nightly job and takes the first copy now, so you find out today whether
the NAS accepts it. The NAS has to be reachable from the server over SSH.

## 6. Prove it

These are the checks that only count on the real thing. Tick them off in
[ROADMAP.md](../ROADMAP.md) as they pass.

| Check | How |
| --- | --- |
| Only the proxy gets in | `curl -I http://<server IP>/` from anywhere else answers 403, or nothing if the Hetzner firewall drops it |
| Survives a reboot | `ssh <operator>@<server> sudo reboot`, then load the site |
| Mail arrives | send yourself a message through the contact form; look at its headers for SPF, DKIM and DMARC `pass` |
| Errors reach you | `ssh <operator>@<server> 'cd /opt/lauridsen-fotos/current && sudo docker compose exec app python manage.py test_error_report'` |
| Uptime alert | point UptimeRobot at `https://<domain>/healthz`, which goes through the proxy; stop the stack, wait for the alert, start it again |
| Backups run unattended | after a few nights, look for dated directories on the NAS |
| Restore | `ansible-playbook playbooks/restore.yml -J` against a second, scratch server |
| Galleries expire | create one, set its expiry to tomorrow, check the day after that its files are gone |

## Afterwards

| When | Run |
| --- | --- |
| You have merged something | `ansible-playbook playbooks/deploy.yml -J` — deploys `main` |
| You have tagged a release | `ansible-playbook playbooks/deploy.yml -J -e deploy_ref=<tag>` |
| Monthly, or after a security announcement | `ansible-playbook playbooks/update.yml -J` |
| Something is badly wrong | `ansible-playbook playbooks/deploy.yml -J -e deploy_ref=<an earlier tag>` |

## Rehearsing a change first

`scripts/vm.sh up` starts two throwaway Debian machines on this Mac — one as the server, one
as the NAS — and `ansible-playbook -i inventory/disposable playbooks/<name>.yml` runs any
playbook against them. The second machine also plays the reverse proxy in front, with a certificate from
Caddy's own test CA, and the server there is handed the commit you have checked out, so a
change can be rehearsed before it is pushed. `scripts/vm.sh down` deletes both.
