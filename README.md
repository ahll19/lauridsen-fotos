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
| Publish photographs, text and prices | [Using the admin](#using-the-admin) |
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

## Using the admin

Everything on the site that is not code is edited in the admin: photographs, albums, page
text, prices and client galleries. You never edit code to publish.

The admin is at `https://lauridsen-fotos.dk/<admin path>/`, where the path is a secret
(`scripts/vault.sh view` shows it as `vault_django_admin_path`). The login is the one made in
[step 6](#6-create-your-admin-login) of the server setup. The admin is in Danish, so the names
below are the ones on screen.

### Publish an album

1. **Kategorier → Tilføj** if the album needs a new category, such as Bryllup or Portræt,
   and tick **Synlig**. A category stays off the site until it has a public album, so it
   never shows empty.
2. **Albummer → Tilføj**. Choose the category and give the album a name. **Kort-navn** fills
   itself in from the Danish name and becomes the album's address, so don't change it once
   the album is public.
3. Under **Tilføj billeder**, select all the photographs at once and press **Gem og fortsæt med
   at redigere**. They are added in the order you selected them.
4. Put them in order with the arrows on each row (top, up, down, bottom). An arrow saves
   straight away, so save any text you have typed first.
5. Give each photograph a caption if you want one shown, and an **alt-tekst** describing what
   is in it, for visitors who cannot see it and for search engines.
6. Tick **Synlig** on the album and save. The album is public when both it and its category
   are ticked; leaving the category unticked keeps a whole category private while you
   prepare it.

The first visit to a new album takes a few seconds, while the site makes the sizes it
shows. After that it is instant.

**Cover.** An album's first photograph is its cover on the portfolio pages, unless you upload
a different one under **Forsidebillede**.

**The front page** shows the newest public album and the newest timeline entry. **Forside**
switches either off, and is where the large image at the top is set.

### What to upload

JPEG. A file the site cannot open as an image, such as a phone's HEIC, a RAW file or a PDF,
is refused, and then nothing in that save is stored: the message names the files to export
as JPEG and upload again.

Full-size exports are fine, but the public site never shows more than 2000 pixels across.
Exporting at 2500 pixels on the long edge uploads several times faster and looks the same.

One save takes up to 1000 MB, which is 40 or more full-size camera JPEGs. For more than that,
upload in batches and save between them.

Location data in the files is removed from everything on the public pages, whose images are
resized copies. The originals are kept on the server but never served. Client galleries are
the exception: the client downloads the files exactly as uploaded.

### Links in text

Descriptions, captions and page text can link elsewhere. A web address written out in full,
`https://…` or `www.…`, becomes a link by itself. To make words the link instead, write:

```text
Læs mere om [udstillingen](https://www.museumforpapirkunst.dk/dk/lyndi-sales-genskaer).
```

The address can also be a page on this site, such as `[kontakt mig](/kontakt/)`, or an email
address as `mailto:navn@domæne.dk`. Nothing else is turned into a link, and HTML typed into
a field is shown as text, never run.

### Timeline entries

**Tidslinjeindlæg → Tilføj**: a title, a date, a short story and a set of photographs, added
and ordered the same way as an album. An entry is public when **Synlig** is ticked. The
timeline is separate from the portfolio: entries are grouped by tags, not categories. To
point an entry at an album, link to it in the story.

**Tags** are picked from one shared list, so the same subject is spelled the same way year
after year. Start typing in the tags field to search the list; the **+** beside it adds a
tag that isn't there yet. Names differing only in capitals count as the same tag.

Each tag has a Danish and an English name, shown on the site in the visitor's language. The
English name can wait: until it is filled in, the English site shows the Danish one.

The list itself is under **Tags**, with how many entries use each. If two tags mean the same
thing, tick both and run **Slå de valgte tags sammen til ét**: every entry moves to the more
used one and the other is deleted. Renaming a tag renames it on every entry.

Visitors can filter the timeline by any tag that a public entry carries.

### Page text and prices

**Forside**, **Om-side**, **Kontaktside** and **Prisside** each have one page of settings
instead of a list. That is where the front page's tagline and introduction, the About text
and portrait, and the contact details are.

**Prispakker** are the packages on the pricing page, ordered with the arrows. Each one's
enquiry button opens the contact form with the package already filled in, so you know what
prompted an enquiry.

Messages sent through the contact form are kept under **Henvendelser**, whether or not their
email arrived.

### Danish and English

Text fields come in pairs marked **[da]** and **[en]**. Fill in Danish first: anything left
without an English version shows the Danish text on the English site rather than an empty
page.

### Client galleries

The part with real consequences, so it is worth knowing how it behaves.

1. **Klientgallerier → Tilføj**. Give it a label for your own use, the client's name and an
   expiry date (90 days out by default), add the photographs and save. Upload full size:
   the client downloads exactly what you upload.
2. **Copy the password from the message at the top.** It is shown once and cannot be
   recovered, though **Generer ny adgangskode** issues a new one.
3. Tick the gallery in the list and run **Byg download-ZIP igen**, or the download-all button
   has nothing behind it. Do it again whenever photographs are added.
4. Send the client the link and the password. Until they enter it the page reveals nothing:
   no thumbnails, no filenames, not even how many photographs there are.

On the expiry date a scheduled job deletes the photographs from disk. The link keeps
answering for another month with a "no longer available" notice, so a client arriving late
gets an explanation rather than a dead link, and then the record goes too. **Forlæng med 30
dage** postpones it; **Luk nu** deletes the photographs at once. Deleting a gallery by hand
removes its files the same way.

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

If the domain already has a mailbox provider, it already has an SPF record. A domain may
only have one, so add `ip4:<address>` to it rather than publishing a second:
`v=spf1 include:zohomail.eu ip4:<address> ~all`.

Test it by sending yourself a message through the contact form. The message is kept under
**Contact submissions** in the admin whether or not the mail arrives. If it does not arrive,
the relay's log on the server says what the receiving server answered:

```bash
sudo docker logs lauridsen-fotos-postfix-1 2>&1 | grep status=
```

`status=sent` means it was accepted. `status=bounced` is followed by the reason.

### 8. Backups

> **Not usable on the live server yet.** The backup job runs on the server and pushes to the
> NAS over SSH. The live server sits in its own network segment and cannot reach anything on
> the LAN, the NAS included, so the job has nowhere to send to. Backups need to be turned
> around, so that something on the LAN collects them from the server. Until then, the live
> site has no backups. The steps below are for a server that can reach its backup target.

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
