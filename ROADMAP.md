# Roadmap to 1.0.0

**1.0.0 means the site is live on the VPS at the real domain, with TLS, backups and
monitoring all working and proven.** Content can keep arriving afterwards — a thin portfolio
does not block the tag. What blocks it is anything that would make the site unsafe to point
real clients at.

Milestones are dependency-ordered, not dated. Each has a definition of done that is meant to
be checkable rather than a matter of opinion: something either happened or it did not.
Versions follow the rules in [CLAUDE.md](CLAUDE.md) and are cut with `scripts/release.sh`.

| Version | Milestone | Blocks 1.0? |
| --- | --- | --- |
| 0.1.0 | Design documents, working rules, and the application running locally | done |
| 0.2.0 | [Visual identity](#020--visual-identity) | done |
| 0.3.0 | [Production configuration, proven locally](#030--production-configuration-proven-locally) | done |
| 0.4.0 | [Host tooling: the `ansible/` directory](#040--host-tooling-the-ansible-directory) | yes |
| 0.5.0 | [The VPS exists and serves the site](#050--the-vps-exists-and-serves-the-site) | yes |
| 0.6.0 | [Day-two operations: backups, monitoring, maintenance](#060--day-two-operations-backups-monitoring-maintenance) | yes |
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
milestone's list, but a Jinja template belongs next to the vault that fills it, which is
0.4.0's work. What 0.3.0 delivers instead is the input that template needs: every variable
documented, with its production value and how to generate it.

---

## 0.4.0 — Host tooling: the `ansible/` directory

The server should be reproducible rather than a pet. Everything from a bare Debian install
upwards is described as playbooks in this repository and applied over SSH, so the host can be
rebuilt from a clone rather than from memory. See
[ADR 0002](docs/decisions/0002-manage-the-host-with-ansible.md) for the reasoning, and
`architecture.md` §10 for where it sits in the architecture.

**Shape**

```
ansible/
  ansible.cfg
  requirements.yml            collections, pinned
  inventory/production/
    hosts.yml
    group_vars/all/
      vars.yml                non-secret configuration
      vault.yml               ansible-vault encrypted
  playbooks/
    provision.yml             bare host → ready to run the stack
    deploy.yml                pull, build, migrate, restart, verify
    update.yml                OS patches, image bumps, dependency review, redeploy
    backup.yml                install the nightly job and its rotation
    restore.yml               pull a backup back onto a host
  roles/
    common/ firewall/ docker/ app/ backup/
```

**Definition of done**

- [ ] `provision.yml` takes a bare Debian 12 host to the state `architecture.md` describes:
      packages, non-root user, SSH hardening, `ufw`, `unattended-upgrades`, Docker Engine and
      the Compose plugin, and the `/data` layout with correct ownership.
- [ ] `deploy.yml` pulls the code, builds the image on the host, runs migrations, restarts
      the stack, and **fails if `/healthz` does not answer afterwards** — a deploy that
      quietly leaves the site down is worse than one that errors.
- [ ] `update.yml` performs the maintenance pass from `architecture.md` §10: OS security
      patches, pinned image bumps, dependency review, then redeploy.
- [ ] `backup.yml` and `restore.yml` exist; they are *exercised* in 0.6.0, not here.
- [ ] Secrets live in `ansible-vault`-encrypted files committed to the repository; the vault
      password is in the password manager and is not in the repository, not in `.env`, and
      not in shell history.
- [ ] The production `.env` is a rendered artefact rather than a hand-edited file: a
      template in `ansible/` filled from the vault. Moved here from 0.3.0, which documented
      every variable it needs but had nowhere to put the template itself.
- [ ] `requirements.yml` pins the collections used, so a fresh machine resolves the same
      versions.
- [ ] Every playbook is idempotent: a second consecutive run reports zero changed tasks.
      This is the check that separates a playbook from a shell script.
- [ ] `provision.yml` and `deploy.yml` have been run end to end against a **disposable**
      host — a throwaway VPS or a local VM — not first attempted on the real one.
- [ ] `ansible-lint` is clean and wired into `scripts/verify.sh`.
- [ ] No configuration step exists outside Ansible. If a document anywhere says "then SSH in
      and…", that step is a bug.

---

## 0.5.0 — The VPS exists and serves the site

`architecture.md`, made real, entirely through the playbooks from 0.4.0. The site answers on
the domain over HTTPS but is not yet announced to anyone.

**Definition of done**

- [ ] Hetzner VPS ordered: Debian 12, roughly 4–8 GB RAM and ~200 GB disk.
- [ ] The host reached its configured state by running `provision.yml` against it, and
      nothing else. Anything discovered mid-flight that had to be fixed by hand is folded
      back into a role before this milestone closes.
- [ ] The Hetzner Cloud Firewall allows only 80, 443 and SSH, matching what `ufw` enforces
      on the host.
- [ ] DNS A (and AAAA if used) pointing at the VPS.
- [ ] `certbot` added to the compose stack; a valid Let's Encrypt certificate is served,
      HTTP redirects to HTTPS, and HSTS is on.
- [ ] A renewal dry run succeeds (`certbot renew --dry-run`) — the certificate expiring
      silently in 90 days is the classic way this setup dies.
- [ ] The application was deployed by `deploy.yml`, and the stack comes back unattended
      after a `reboot`.
- [ ] Admin reachable at the secret path, with a superuser created interactively; the path
      comes from the vault, not from the repository in plaintext.
- [ ] Containers run as non-root, and `/data` is owned by that user only.
- [ ] **Mail actually arrives.** Moved here from 0.3.0, which built the relay but could not
      prove delivery — that depends on the host and its DNS, neither of which existed
      ([ADR 0004](docs/decisions/0004-deliver-mail-directly-rather-than-through-a-smarthost.md)).
      Specifically: Hetzner asked to unblock outbound port 25, which is closed by default on
      new accounts; reverse DNS set on the VPS to `MAIL_HOSTNAME`; an SPF record naming the
      VPS; a DKIM key generated, mounted, and its public half published at
      `mail._domainkey`. Then a contact-form submission sent from the live site lands in a
      real inbox, in the inbox rather than the spam folder, and its headers show SPF, DKIM
      and DMARC all passing. Checking the queue is not evidence — mail that is accepted and
      then filed as spam looks identical to mail that worked.

---

## 0.6.0 — Day-two operations: backups, monitoring, maintenance

Nothing here counts as done because it was configured. It counts as done because it was
tested and observed to work.

**Definition of done**

- [ ] Nightly `rsync` of `/data` to the home NAS, excluding the cache subpath, installed by
      `backup.yml` and observed to have run unattended for several consecutive nights.
- [ ] Retention keeps the most recent 14 copies, and older ones are actually being pruned.
- [ ] **A restore drill has been performed** by running `restore.yml` against a scratch
      host: the site comes up with the database and photographs intact. The date it was done
      and how long it took are written down. A restore procedure nobody has run is a
      hypothesis.
- [ ] `update.yml` has been run at least once against the real host, and the site was still
      healthy afterwards.
- [ ] Losing the vault password is understood as a disaster-recovery scenario: the password
      manager entry holding it is itself backed up (ADR 0002).
- [ ] UptimeRobot (or equivalent) checking `/healthz`, alerting somewhere you will actually
      see it — verified by deliberately stopping the stack and receiving the alert.
- [ ] An unhandled error produces an email through the relay — verified deliberately, not
      assumed.
- [ ] `expire_galleries` and `purge_tombstoned_galleries` confirmed from production logs to
      have run on their schedule, with a real gallery expiring and its files leaving disk.

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
