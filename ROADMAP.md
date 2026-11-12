# Roadmap to 1.0.0

**1.0.0 means the site is live on the VPS at the real domain, with TLS, backups and
monitoring all working and proven.** Content can keep arriving afterwards — a thin portfolio
does not block the tag. What blocks it is anything that would make the site unsafe to point
real clients at.

**Where it stands.** Everything that can be built and proven without a server is. What is
left needs things only Anders can supply — a VPS, a domain, the NAS, real photographs — and
[docs/go-live.md](docs/go-live.md) is the list, in order, with the command for each step.
That state is tagged `v1.0.0-rc.1`; further candidates follow as the server turns things up,
and 1.0.0 is the one that is live.

Milestones are dependency-ordered, not dated. Each has a definition of done that is meant to
be checkable rather than a matter of opinion: something either happened or it did not.
Versions follow the rules in [CLAUDE.md](CLAUDE.md) and are cut with `scripts/release.sh`.

| Version | Milestone | Blocks 1.0? |
| --- | --- | --- |
| 0.1.0 | Design documents, working rules, and the application running locally | done |
| 0.2.0 | [Visual identity](#020--visual-identity) | done |
| 0.3.0 | [Production configuration, proven locally](#030--production-configuration-proven-locally) | done |
| 0.4.0 | [Host tooling: the `ansible/` directory](#040--host-tooling-the-ansible-directory) | done |
| 0.5.0 | [The VPS exists and serves the site](#050--the-vps-exists-and-serves-the-site) | yes — rehearsed, needs the server |
| 0.6.0 | [Day-two operations: backups, monitoring, maintenance](#060--day-two-operations-backups-monitoring-maintenance) | yes — rehearsed, needs the server |
| 1.0.0 | [Live](#100--live) | — |

---

## 0.2.0 — Visual identity

**Done**, released as `v0.2.0`. Settled on **Atelier Sage** — see
[ADR 0003](docs/decisions/0003-visual-direction-atelier-sage.md). Confirmed by a
teardown-and-rebuild QA walkthrough of the running site before the release, which found five
defects, all fixed ([D34–D38](docs/defects.md)).

Four complete directions were built and made switchable on the running site, so they could be
judged against real photographs rather than mockups. Atelier won; a second round then varied
it one axis at a time (accent hue, temperature, typography) so a preference was attributable
to a single change. The sage accent recedes where the original terracotta advanced, which is
what an accent on a photography site should do.

**Definition of done**

- [x] Four directions viewable locally as real pages, not mockups.
- [x] One direction chosen.
- [x] Chosen direction applied to every page type: home, portfolio index/category/album,
      timeline index/entry, pricing, contact, about, and all three gallery states
      (locked, unlocked, expired). It lives in `site.css`, so this is structural.
- [x] Renders correctly at 360px, 768px and 1440px with no horizontal scroll. Every grid is
      `minmax(min(100%, X), 1fr)` and the page gutter is `min(100% - 2.5rem, …)`, so nothing
      can exceed the viewport; breakpoints at 760/800/860px.
- [x] `prefers-reduced-motion` honoured.
- [x] Still no CSS framework, no bundler, no Node — per `technical_design.md`.
- [x] Preview machinery removed: the switcher, the comparison page, the candidate
      stylesheets and the `DESIGN_PREVIEW_ENABLED` setting are all gone.

---

## 0.3.0 — Production configuration, proven locally

Everything that must work differently in production, made to work *before* paying for a
server. Finding these on a live host is worse in every way.

**Definition of done**

- [x] The stack runs locally with `DJANGO_DEBUG=0`, and every page returns 200 —
      production uses `ManifestStaticFilesStorage` and a stricter security posture, which is
      a genuinely different code path. `scripts/prodcheck.sh` runs the stack that way and
      crawls it; currently 125 URLs, all 200.
- [x] `manage.py check --deploy` produces no errors, and every remaining warning is
      understood and deliberately accepted. There are none: the run is clean.
- [x] Custom 400, 403, 404 and 500 pages, in both languages, styled like the rest of the
      site. 403 and 400 were added alongside the two asked for, because a stale form's CSRF
      failure produced exactly the same unstyled English page the milestone exists to remove.
- [x] Mailpit swapped for a real outbound-only Postfix relay; a contact-form submission is
      **accepted into the relay's queue**, the relay refuses to send as any other domain,
      and it is configured to deliver straight to recipients ([ADR 0004](docs/decisions/0004-deliver-mail-directly-rather-than-through-a-smarthost.md)).
- [x] `.env.example` documents how to generate every production secret, and carries a
      visible warning that its defaults are for local use only.

**Two things changed shape while this was built**, both recorded in ADR 0004:

*Deliverability moved to 0.5.0.* The original wording asked for a submission that "arrives
in a real inbox and does not land in spam". That cannot be proven here at all, and not for
want of trying: it depends on a reverse DNS record on a host that does not exist, an SPF
record naming an IP that has not been allocated, and a DKIM key published in a DNS zone —
and residential ISPs block outbound port 25 regardless. What is provable locally is the hop
this repository owns, and that is what is checked. The inbox test moves to 0.5.0, next to
DNS and certificates.

*The relay is a second service, not a swapped image.* The `MAIL_RELAY_IMAGE` variable was
supposed to carry the swap. It could not: the two images share no configuration, and worse,
an `.env` still holding the old value started Mailpit under the name `postfix` — a relay
that accepts every message and silently delivers none. Mailpit and Postfix are now separate
compose services chosen by `COMPOSE_PROFILES`, with the image pinned per service.

**Deliberately left out.** "The production `.env` is a rendered artefact" was in this
milestone's list, but a Jinja template belongs next to the vault that fills it, so it was
delivered with 0.4.0.

---

## 0.4.0 — Host tooling: the `ansible/` directory

**Done.** The server is described as playbooks and can be rebuilt from a clone. See
[ADR 0002](docs/decisions/0002-manage-the-host-with-ansible.md) for why,
[ADR 0007](docs/decisions/0007-the-host-pulls-releases-from-the-public-repository.md) for how code
reaches the host, and [ADR 0006](docs/decisions/0006-certbot-keeps-a-certificate-where-nginx-reads-it.md)
for certificates.

Proven on a disposable Debian 12 machine rather than assumed (`scripts/vm.sh`): a bare
host, reachable only as root, taken to a serving site over HTTPS by `provision.yml` and
`deploy.yml` and nothing else. That rehearsal found two defects that would have broken
the first real deploy ([D41, D42](docs/defects.md)).

**Definition of done**

- [x] `provision.yml` takes a bare Debian 12 host to the state `architecture.md` describes:
      packages, non-root user, SSH hardening, `ufw`, `unattended-upgrades`, Docker Engine and
      the Compose plugin, and the `/data` layout with correct ownership. Afterwards root and
      password logins are both refused, and only 22, 80 and 443 are open.
- [x] `deploy.yml` ships the code, builds the image on the host, runs migrations, restarts
      the stack, and **fails if `/healthz` does not answer afterwards**. Seen failing for
      exactly that reason during the rehearsal, before D42 was fixed.
- [x] `update.yml` performs the maintenance pass from `architecture.md` §10: OS security
      patches, a rebuild on freshly pulled base images, a list of dependencies with newer
      releases to review, then redeploy.
- [x] `backup.yml` and `restore.yml` exist — and were exercised, which was 0.6.0's job.
- [x] Secrets live in an `ansible-vault` file; `scripts/vault.sh init` generates every one
      and writes it encrypted. **Not yet created**: the vault's password should be chosen
      by Anders and never touch a disk, so `init` is his to run
      ([go-live](docs/go-live.md)). `verify.sh` fails if a vault file is ever committed
      unencrypted.
- [x] `requirements.yml` pins the collections used.
- [x] Every playbook is idempotent: `provision`, `deploy`, `update` and `backup` each report
      zero changed tasks on a second consecutive run. `restore` refuses to run twice.
- [x] `provision.yml` and `deploy.yml` have been run end to end against a disposable host.
- [x] `ansible-lint` is clean at its strictest profile and wired into `scripts/verify.sh`.
- [x] No configuration step exists outside Ansible. The two things done to *other* systems
      — a DNS record, a key on the NAS — are printed by `scripts/vault.sh public`.
- [x] The production `.env` is a rendered artefact (carried over from 0.3.0):
      `ansible/roles/app/templates/env.j2`, and `verify.sh` fails if a key in `.env.example`
      is missing from it.

---

## 0.5.0 — The VPS exists and serves the site

`architecture.md`, made real, entirely through the playbooks from 0.4.0. The site answers on
the domain over HTTPS but is not yet announced to anyone.

Every item below that could be rehearsed has been, on the disposable machine, with Pebble
(Let's Encrypt's test server) standing in for Let's Encrypt. A box stays unticked until it
has happened on the real host. [docs/go-live.md](docs/go-live.md) is the order to do them in.

**Definition of done**

- [ ] Hetzner VPS ordered: Debian 12, roughly 4–8 GB RAM and ~200 GB disk.
- [ ] The host reached its configured state by running `provision.yml` against it, and
      nothing else. *Rehearsed.*
- [ ] The Hetzner Cloud Firewall allows only 80, 443 and SSH, matching what `ufw` enforces
      on the host.
- [ ] DNS A (and AAAA if used) pointing at the VPS.
- [ ] A valid Let's Encrypt certificate is served, HTTP redirects to HTTPS, and HSTS is on.
      *Rehearsed*: `certbot` is in the stack; a certificate was issued over HTTP-01, HTTP
      answered 301 to HTTPS, and `Strict-Transport-Security` was present.
- [ ] A renewal dry run succeeds (`certbot renew --dry-run`). *Partly rehearsed*: a real
      renewal was forced against the test CA, the new certificate was put in place, and
      nginx reloaded by itself and served it. The dry run itself needs the real domain.
- [ ] The application was deployed by `deploy.yml`, and the stack comes back unattended
      after a `reboot`. *Rehearsed*: healthy again within a minute of the reboot.
- [ ] Admin reachable at the secret path, with a superuser created interactively; the path
      comes from the vault, not from the repository in plaintext.
- [ ] The application container runs entirely as uid 1000, PID 1 included, and `/data` is
      owned by that user only. *Rehearsed.* `app-cron` is the deliberate exception: its
      PID 1 is the cron daemon, which must be root to drop to `app` for each job. Tracked
      in [docs/defects.md](docs/defects.md); `supercronic` would remove it, still undecided.
- [ ] **Mail actually arrives.** Hetzner asked to unblock outbound port 25; reverse DNS set
      to `MAIL_HOSTNAME`; an SPF record naming the VPS; the DKIM public key published
      (`scripts/vault.sh public` prints it). Then a contact-form submission from the live
      site lands in a real inbox, not the spam folder, with SPF, DKIM and DMARC passing.
      *Rehearsed as far as the relay*: the message was accepted and DKIM-signed with the
      vault's key, and a foreign sender was refused. Delivery cannot be rehearsed
      ([ADR 0004](docs/decisions/0004-deliver-mail-directly-rather-than-through-a-smarthost.md)).

---

## 0.6.0 — Day-two operations: backups, monitoring, maintenance

Nothing here counts as done because it was configured. It counts as done because it was
tested and observed to work — on the real host. The rehearsal is evidence the tooling
works, not a substitute.

**Definition of done**

- [ ] Nightly `rsync` of `/data` to the home NAS, excluding the cache subpath, installed by
      `backup.yml` and observed to have run unattended for several consecutive nights.
      *Rehearsed* against a second machine playing the NAS: photographs and a consistent
      snapshot of the database arrived, the cache did not.
- [ ] Retention keeps the most recent 14 copies, and older ones are actually being pruned.
      *Rehearsed* with a retention of 2: the third run removed the first copy.
- [ ] **A restore drill has been performed** by running `restore.yml` against a scratch
      host. *Rehearsed on 2026-11-11*: the server was destroyed and a bare one built,
      provisioned and restored from the NAS alone in **2 minutes 34 seconds**. Album, photo,
      timeline, gallery and enquiry counts were identical, and the client gallery opened
      with its original password. To be repeated once against real data.
- [ ] `update.yml` has been run at least once against the real host, and the site was still
      healthy afterwards. *Rehearsed.*
- [ ] Losing the vault password is understood as a disaster-recovery scenario: the password
      manager entry holding it is itself backed up (ADR 0002).
- [ ] UptimeRobot (or equivalent) checking `/healthz`, alerting somewhere you will actually
      see it — verified by deliberately stopping the stack and receiving the alert.
- [ ] An unhandled error produces an email through the relay — verified deliberately.
      `manage.py test_error_report` sends one on demand. *Rehearsed as far as the relay.*
- [ ] `expire_galleries` and `purge_tombstoned_galleries` confirmed from production logs to
      have run on their schedule, with a real gallery expiring and its files leaving disk.
      *Rehearsed*, and it mattered: the jobs had never run at all ([D41](docs/defects.md)).

---

## 1.0.0 — Live

**Definition of done**

- [ ] Every milestone above complete.
- [ ] Real content published: at least one portfolio category with a real album, About and
      Contact filled in, and pricing packages showing real prices.
- [ ] Everything published has both Danish and English filled in — the fallback exists, but
      shipping visible Danish on the English site is a rough edge.
- [ ] One client gallery created, shared, and downloaded end to end — with a real client if
      the timing works, otherwise as a full rehearsal including the expiry.
- [ ] `robots.txt` and `sitemap.xml` correct on the live domain, with no client gallery
      appearing in either.
- [ ] You have published a new album yourself, through the admin, without asking anyone for
      help. This is the real test of the whole thing.
- [ ] Tagged with `scripts/release.sh`.

---

## After 1.0.0

Good ideas, none of them blocking. Roughly in the order they are likely to become worth
doing.

- **Cookie notice and privacy policy** — the site currently sets only strictly necessary
  cookies (session, CSRF, language), which need no consent banner under EU rules. That
  changes the day analytics arrive, and a privacy policy page is worth having regardless for
  a business handling client photographs.
- **Accessibility pass** — keyboard navigation, visible focus states, colour contrast, and
  alt-text discipline in the admin. Partly there; a deliberate pass would make it solid.
- **Jenkins CI/CD** — build and deploy from Jenkins with a registry in between, rather than
  building on the VPS. Cheap once the Ansible work is done: Jenkins calls `deploy.yml`
  instead of you calling it, so the deployment logic doesn't move. `architecture.md` §10
  already notes this needs no re-architecting.
- **A staging host** — a second, cheaper VPS built from the same playbooks with a different
  inventory. Worth it the first time an upgrade needs rehearsing before it touches
  production; unnecessary before that.
- **restic or borg backups** — snapshotting, deduplicating, encrypted at rest. Worth it when
  `/data` grows large enough that full nightly copies get expensive.
- **Dead-man's-switch on the scheduled jobs** — detects the expiry job silently not running,
  which is the one failure mode that is invisible until a client's photographs outlive their
  expiry date. Deliberately out of scope in `architecture.md` §9.
- **Cloudflare Turnstile** — only if the honeypot and rate limit stop being enough.
- **Image pipeline tuning** — AVIF/WebP derivatives and `srcset`, if page weight becomes a
  real problem on mobile connections.

Explicitly not planned, per `functional_design.md` §10: e-commerce, print ordering, online
payments, visitor accounts, and comments on timeline entries.
