# Going live

The site is built and the path to production has been rehearsed on a disposable server.
What remains needs things only you have. This is that list, in the order to do it.

Each step is one command or one thing to click. If a step ever needs you to SSH in and
type something, that is a bug in a playbook — fix the playbook.

## 1. Decide and order

1. **A server.** Hetzner Cloud, Debian 12, 4–8 GB RAM. Add your SSH public key when
   ordering, so root accepts it.
2. **A domain**, and an A record for it (and for `www`) pointing at the server.
3. **Make the repository public.** The server pulls the code from GitHub and holds no
   credential for it, so a deploy fails while the repository is private.
4. **Ask Hetzner to open outbound port 25.** It is closed on new accounts and opened on
   request; without it no mail leaves. This can take a day, so ask early.

## 2. Tell the playbooks

Edit two files in `ansible/inventory/production/`:

| File | Set |
| --- | --- |
| `hosts.yml` | `ansible_host` — the server's IP address |
| `group_vars/all/vars.yml` | `site_domain`, `owner_email`, `letsencrypt_email`, and `letsencrypt_agree_tos: true` once you have read their agreement |

Then create the secrets. You will be asked to choose the vault password; put it in your
password manager straight away, because it is the only copy.

```bash
scripts/vault.sh init
```

Commit all three files and merge them to `main`. The vault is encrypted and is meant to be
committed; the other two hold nothing the site's DNS does not already publish, apart from
the two email addresses.

## 3. Build the server

```bash
scripts/ansible.sh provision
```

```bash
scripts/ansible.sh deploy
```

The first takes a bare server to a hardened one running Docker. The second has the
server pull `main` from GitHub, builds it, starts the stack, obtains the certificate and fails unless
`https://<your domain>/healthz` answers. Both are safe to run again.

Then create your admin account:

```bash
ssh -t deploy@<server> 'cd /opt/lauridsen-fotos/current && sudo docker compose exec app python manage.py createsuperuser'
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
| Firewall: 22, 80, 443 only | Hetzner Cloud Firewall, attached to the server |

## 5. Backups

Set `backup_target_host` (and user, port, path if they differ) in `vars.yml`, then:

```bash
scripts/ansible.sh backup -e backup_run_now=true
```

That installs the nightly job and takes the first copy now, so you find out today whether
the NAS accepts it. The NAS has to be reachable from the server over SSH.

## 6. Prove it

These are the checks that only count on the real thing. Tick them off in
[ROADMAP.md](../ROADMAP.md) as they pass.

| Check | How |
| --- | --- |
| Certificate renewal | `ssh deploy@<server> 'cd /opt/lauridsen-fotos/current && sudo docker compose exec certbot certbot renew --dry-run'` |
| Survives a reboot | `ssh deploy@<server> sudo reboot`, then load the site |
| Mail arrives | send yourself a message through the contact form; look at its headers for SPF, DKIM and DMARC `pass` |
| Errors reach you | `ssh deploy@<server> 'cd /opt/lauridsen-fotos/current && sudo docker compose exec app python manage.py test_error_report'` |
| Uptime alert | point UptimeRobot at `https://<domain>/healthz`, stop the stack, wait for the alert, start it again |
| Backups run unattended | after a few nights, look for dated directories on the NAS |
| Restore | `scripts/ansible.sh restore` against a second, scratch server |
| Galleries expire | create one, set its expiry to tomorrow, check the day after that its files are gone |

## Afterwards

| When | Run |
| --- | --- |
| You have merged something | `scripts/ansible.sh deploy` — deploys `main` |
| You have tagged a release | `scripts/ansible.sh deploy -e deploy_ref=<tag>` |
| Monthly, or after a security announcement | `scripts/ansible.sh update` |
| Something is badly wrong | `scripts/ansible.sh deploy -e deploy_ref=<an earlier tag>` |

## Rehearsing a change first

`scripts/vm.sh up` starts two throwaway Debian machines on this Mac — one as the server, one
as the NAS — and `scripts/ansible.sh -I disposable <playbook>` runs any playbook against
them. Certificates there come from a test CA, and the server
there is handed the commit you have checked out, so a change can be rehearsed before it is
pushed. `scripts/vm.sh down` deletes both.
