# Lauridsen Fotos

A photography portfolio and client delivery site: public albums, a photo-led timeline,
pricing and contact pages, and private client galleries that delete themselves when they
expire.

Django behind nginx on a single Docker Compose stack, in Danish and English. No build step —
server-rendered templates and hand-written CSS.

Live at <https://lauridsen-fotos.dk>.

| To | Read |
| --- | --- |
| Run it on your own machine | [Running it](#running-it) |
| Publish albums and prices | [Publishing](#publishing) |
| Deliver photographs to a client | [Client galleries](#client-galleries) |
| Change a port, a schedule or a limit | [Configuration](#configuration) |
| Set up or update the server | [Deploying to a server](#deploying-to-a-server) |
| Change the code | [Working on the code](#working-on-the-code) |
| Look something up | [Reference](#reference) |

## Running it

Docker is the only requirement.

```bash
cp .env.example .env
scripts/install-hooks.sh   # once per clone
scripts/dev.sh up
scripts/dev.sh seed        # demo content, if you want something to look at
scripts/dev.sh superuser   # your admin login
```

The site is then at <http://localhost:8080/> and the admin at `/studio-admin/` — not
`/admin/`, since that path is a shared secret in production. Every email the site sends is
caught at <http://localhost:8025/> rather than delivered. `scripts/dev.sh urls` prints all
of them.

Danish is the default and has no URL prefix; English lives under `/en/`. The URL decides the
language, so a link opens in the language you sent it in.

## Publishing

Everything is managed in the admin. You never edit code to publish.

Albums live under Portfolio, inside a category. Upload as many photographs at once as you
like, drag them into order, and set a cover if you don't want the first one used. An album
is public only when both it and its category are marked *synlig*, which lets you prepare a
whole category in private. Timeline entries work the same way — a title, a date, a short
story, a photo set.

Page text and prices are single records rather than lists: one Forside, one Om-side, one
Kontaktside, plus the pricing packages. Each package's enquiry button links to the contact
form with the package name already filled in, so you know what prompted an enquiry.

Translatable fields show Danish and English side by side. Fill in Danish first — anything
left untranslated falls back to it rather than rendering an empty page.

## Client galleries

The part with real consequences, so it is worth knowing how it behaves.

Create one under Klientgallerier with a label for your own reference, the client's name, an
expiry date (90 days out by default) and the photographs. On save the admin shows the
password once. It is hashed immediately and cannot be recovered, though you can issue a new
one later. Then run the *Byg download-ZIP igen* action, or the download-all button has
nothing behind it.

Send the client the link and the password. Until they enter it the page reveals nothing — no
thumbnails, no filenames, not even how many photographs there are.

On the expiry date a scheduled job deletes the photographs from disk. The URL keeps
answering for another month with a "no longer available" notice, so a client arriving late
gets an explanation rather than a dead link, and then the record goes too. Deleting a gallery
by hand removes its files the same way.

## Configuration

Ports, schedules, expiry windows, the admin path and upload limits all come from `.env`, and
`.env.example` documents every one. Edit it, then restart:

```bash
scripts/dev.sh down && scripts/dev.sh up
```

Quote any value containing a space or an asterisk — `"0 3 * * *"` — because the scripts read
the file with the shell.

Switching the mail relay means changing three values together:

| | Mailpit, for development | Postfix, as production runs |
| --- | --- | --- |
| `COMPOSE_PROFILES` | `dev` | `prod` |
| `EMAIL_PORT` | `1025` | `587` |
| `DEFAULT_FROM_EMAIL` | anything | must be on `MAIL_SENDER_DOMAIN`, or the relay refuses it |

`DJANGO_DEBUG` and `STATIC_CACHE_CONTROL` travel together too: `immutable` is only ever a
true thing to say about a filename carrying a content hash, which is what `DJANGO_DEBUG=0`
produces. `scripts/prodcheck.sh` sets both correctly, so prefer it to changing them by hand.

## Deploying to a server

The server is built and deployed with Ansible, run from `ansible/` on your own machine.
Nothing is done by hand on the server. Once it is set up, a deploy is one command:

```bash
cd ansible && ansible-playbook playbooks/deploy.yml -J
```

`-J` asks for the vault password. The steps below are the first time, in order.
[ansible/README.md](ansible/README.md) is the reference for every command.

### What you need

- **A server** running Debian 13 (12 works too) that you can SSH to with your own account and
  password, and its root password.
- **A reverse proxy in front** that holds the TLS certificate and forwards to the server's
  port 80 over plain HTTP. It must pass `Host` through, set `X-Forwarded-Proto: https`,
  append the visitor's address to `X-Forwarded-For`, and allow uploads of 100 MB taking up
  to five minutes.
- **A domain** pointing at that proxy.
- **An SSH key** on your machine. `ssh-keygen -t ed25519` makes one.

### 1. Install the tools

Once per machine:

```bash
brew install ansible sshpass
```

```bash
cd ansible && ansible-galaxy collection install -r requirements.yml
```

### 2. Describe the server

Four files in `ansible/inventory/production/`:

| File | Set |
| --- | --- |
| `hosts.yml` | `ansible_host`: the server's address |
| `group_vars/all/vars.yml` | `operator_user`: your account on the server |
| | `site_domain` and `site_alternate_domains` |
| | `owner_email`: where contact messages and error reports go. Deploy refuses to run while it is empty |
| | `upstream_proxy_addresses`: the proxy's address as the server sees it connect. nginx refuses everyone else |
| `group_vars/all/trusted_keys.yml` | Your SSH public key. The file says how to add it |
| `group_vars/all/vault.yml` | The secrets. Created once with `scripts/vault.sh init`, which asks you to choose the vault password. Keep that in a password manager: it is the only copy |

Commit them. The vault is encrypted and is meant to be committed.

### 3. Provision

From `ansible/`. This one run logs in with passwords, because the server does not have your
key yet:

```bash
ansible-playbook playbooks/provision.yml -J -k -K --become-method su
```

| Prompt | Give it |
| --- | --- |
| `SSH password` | your account's password on the server |
| `BECOME password` | root's password on the server |
| `Vault password` | the vault password |

None of the three is stored. The run installs your key, lets your account use sudo, turns
password logins off, sets up the firewall and installs Docker. It refuses to start if your
machine's key is not in `trusted_keys.yml`, so it cannot lock you out.

From now on the server accepts only the trusted keys, and every command needs only `-J`.

### 4. Deploy

```bash
ansible-playbook playbooks/deploy.yml -J
```

The server pulls `main` from GitHub, builds it, starts the stack, and the run fails unless
the site answers. Only what has been pushed can be deployed. To deploy a branch or a tag:

```bash
ansible-playbook playbooks/deploy.yml -J -e deploy_ref=<branch or tag>
```

### 5. Check it

| Check | How |
| --- | --- |
| The site answers through the proxy | open `https://<your domain>/healthz` |
| Only the proxy gets in | `curl -I http://<server address>/` from any other machine answers 403 |
| Password logins are off | `ssh -o PubkeyAuthentication=no <you>@<server>` is refused |

### 6. Create your admin login

```bash
ssh -t <you>@<server> 'cd /opt/lauridsen-fotos/current && sudo docker compose exec app python manage.py createsuperuser'
```

The admin is at `https://<your domain>/<admin path>`. The path is a secret:
`scripts/vault.sh view` shows it as `vault_django_admin_path`.

### 7. Mail

The server delivers mail itself, so it needs outbound port 25 and three DNS records.
Many home and cloud networks block port 25; if yours does, no mail leaves.

```bash
scripts/vault.sh public
```

prints the DKIM value. Then publish:

| Record | Value |
| --- | --- |
| TXT at `mail._domainkey.<domain>` | the DKIM value |
| TXT on the domain | `v=spf1 ip4:<the address mail leaves from> -all` |
| A for `mail.<domain>` | that same address |

Test it by sending yourself a message through the contact form.

### 8. Backups

Set `backup_target_host` in `vars.yml` (and the user, port and path if they differ). Add the
backup key that `scripts/vault.sh public` prints to that account's `authorized_keys` on the
NAS. Then:

```bash
ansible-playbook playbooks/backup.yml -J -e backup_run_now=true
```

That installs the nightly job and takes the first copy now.

### Afterwards

| When | Run, from `ansible/` |
| --- | --- |
| You have merged something | `ansible-playbook playbooks/deploy.yml -J` |
| Something is badly wrong | `ansible-playbook playbooks/deploy.yml -J -e deploy_ref=<an earlier tag>` |
| Monthly, or after a security announcement | `ansible-playbook playbooks/update.yml -J` |
| Another machine should maintain the server | add its key to `trusted_keys.yml`, then `ansible-playbook playbooks/provision.yml -J` |
| The server lost its data | `ansible-playbook playbooks/restore.yml -J` |

To try any of this on a throwaway machine first, see
[Rehearsing on a disposable machine](ansible/README.md#rehearsing-on-a-disposable-machine).

## Working on the code

Branch, verify, then open a pull request:

```bash
scripts/new-branch.sh fix thumbnail-orientation
scripts/verify.sh
```

`main` is protected, commit messages follow Conventional Commits, and the git hooks enforce
both locally. [CLAUDE.md](CLAUDE.md) has the working rules in full.

Production is a different code path, not just a different flag — assets get content-hashed
names, errors become pages instead of tracebacks, and the security middleware stops being
lenient. `scripts/prodcheck.sh` runs the stack that way here and checks it, then puts
development mode back — `--keep` leaves it there if you want to click around. Worth running
before anything that touches templates, static files or settings.

The look is `src/static/css/site.css`, with the palette as custom properties at the top —
changing the accent is two values. Interface strings live in `src/locale/da/`: after touching
one, run `makemessages`, translate the new entries, then `compilemessages`. Content text is
not there; it is in the admin.

Releases happen in two steps, since `main` cannot be pushed to directly:

```bash
scripts/release.sh prepare minor   # bumps VERSION, writes the changelog, opens a pull request
scripts/release.sh tag             # on main, once that is merged
```

---

## Reference

### Scripts

`scripts/dev.sh <command>` runs the local stack:

| | |
| --- | --- |
| `up` | Build if needed, start, wait until the site answers. Safe to repeat. |
| `down` | Stop. Data and photographs stay. |
| `reset` | Stop and delete `./data` — database and every photograph. Asks for confirmation. |
| `logs [service]` | Follow the logs. |
| `manage <command>` | Any Django management command. |
| `seed` | Demo content: categories, albums, timeline entries, an active and an expired gallery. |
| `superuser` | Create an admin account. |
| `shell` | A shell inside the app container. |
| `cron` | Run both scheduled jobs once, now. |
| `urls` | Print where everything is. |

The rest:

| | |
| --- | --- |
| `scripts/verify.sh` | Hygiene, secrets, lint, Django checks, migrations, tests, compose validation. Run before a pull request; `--fast` is the subset the pre-commit hook runs. |
| `scripts/prodcheck.sh` | Runs the stack with production settings and checks it, then restores development mode. `--keep` leaves it in production mode to look around. |
| `scripts/crawl.py <url>` | Follows every link and `src` on the running site and reports anything that is not a 200. Used by `prodcheck.sh`; useful on its own after a template change. |
| `scripts/vault.sh` | `init`, `edit`, `view` the production secrets; `public` prints what goes in DNS and on the NAS. |
| `scripts/vm.sh` | `up`, `rebuild`, `sync`, `ssh`, `down`: disposable machines for rehearsing playbooks. Needs Lima. |
| `scripts/install-hooks.sh` | Points git at `.githooks/`. Once per clone. |
| `scripts/new-branch.sh <type> <slug>` | A correctly named branch off an up-to-date `main`. |
| `scripts/release.sh` | `prepare <major\|minor\|patch>` then `tag`. |

### Layout

```
ansible/         playbooks and roles that build and deploy the server
docker/          Dockerfile, entrypoint, nginx and cron templates
src/
  config/        settings, URLs, WSGI, test runner
  core/          sitemap, health check, proxy middleware, upload field
  portfolio/     Category → Album → Photo
  timeline/      showcase sessions
  pages/         home/about/contact/pricing, packages, contact submissions
  galleries/     password gate, expiry, ZIP delivery
  templates/ static/ locale/
scripts/         dev, verify, release, hooks, branch creation, vault, rehearsal machines
docs/            decision records
```

Four containers: nginx, the application, a cron container for the scheduled jobs, and a mail
relay. All state lives in one bind-mounted directory — `./data` here, `/data` in the
containers — holding the database, the uploaded originals, and a disposable thumbnail cache
that backups skip.

The relay is two services rather than one: Mailpit captures mail and shows it in a browser,
Postfix delivers it straight to recipients
([ADR 0004](docs/decisions/0004-deliver-mail-directly-rather-than-through-a-smarthost.md)).
Both answer to the name `mail-relay`, so the application never knows which is running.

### When something is wrong

- **Old styling after a change** — hard-reload. In development the filenames carry no
  content hash to force a re-fetch.
- **`command not found` from a script** — an unquoted value in `.env`.
- **Port already in use** — change `HTTP_PORT` in `.env`.
- **Docker hangs with no output** — usually the Docker Desktop credential helper. Restart it.
- **The site will not start** — `dev.sh up` prints the last log lines on failure; after a
  code change the usual cause is a pending migration.
- **A photograph 404s after moving an album** — upload paths are built from the slugs at
  upload time and renaming does not move files. Re-upload them.
- **Every request redirects to `https://` and nothing answers** — production settings with
  no TLS-terminating proxy in front. Set `DJANGO_SERVE_OVER_HTTPS=0`, or use `prodcheck.sh`,
  which does.
- **403 from nginx on the server** — the request did not come from an address in
  `upstream_proxy_addresses`. That is nginx refusing anyone but the proxy in front.
- **Mail disappears with no error** — either `COMPOSE_PROFILES` names a relay that is not
  running, or Postfix is running and `DEFAULT_FROM_EMAIL` is not on `MAIL_SENDER_DOMAIN`.

### Documents

[functional_design.md](functional_design.md) covers what the site does, page by page;
[architecture.md](architecture.md) how the hosting environment is built and operated;
[technical_design.md](technical_design.md) how the application implements it. These three are
the source of truth for what gets built.

| Document | Holds |
| --- | --- |
| [ROADMAP.md](ROADMAP.md) | What stands between here and 1.0.0 |
| [CHANGELOG.md](CHANGELOG.md) | What changed in each release |
| [docs/decisions/](docs/decisions/) | Choices that differ from the design documents, and why |
| [ansible/README.md](ansible/README.md) | Every playbook command |
| [CLAUDE.md](CLAUDE.md) | The working rules: branching, commits, releases |
