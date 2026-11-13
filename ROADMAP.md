# Roadmap to 1.0.0

**1.0.0 means the site is live at the real domain, served over HTTPS, with mail, backups and
monitoring proven on the real server, and real content published.** A thin portfolio does
not block the tag. What blocks it is anything that would make the site unsafe to point real
clients at.

**Where it stands.** The site is live at <https://lauridsen-fotos.dk>, built and deployed by
the playbooks alone. What is left is proving the parts that only count on the real server,
and publishing real content. Release candidates (`v1.0.0-rc.N`) are cut along the way.

A box is ticked when the thing has been seen to work on the real server, not when it was
configured. What was built on the way here is in [CHANGELOG.md](CHANGELOG.md).

## The server

- [x] The server reached its state by running `provision.yml`, and nothing else.
- [x] The application was deployed by `deploy.yml`, which fails unless the site answers.
- [x] The site is served over HTTPS through the reverse proxy, plain HTTP redirects to
      HTTPS, and HSTS is on.
- [x] The server refuses anyone but the proxy: a direct request answers 403.
- [x] SSH accepts only the keys in `trusted_keys.yml`. Root and password logins are refused.
- [ ] `www.lauridsen-fotos.dk` answers too. The proxy's certificate does not cover it yet.
- [ ] Visitors' own addresses reach the application. The contact form's rate limit is per
      address, so it must not see every visitor as the router.
- [ ] The stack comes back unattended after a reboot.
- [ ] Admin reachable at the secret path, with a superuser created.

## Mail

- [x] Outbound port 25 is open from the server.
- [ ] The DKIM, SPF and `mail.<domain>` records are published
      (`scripts/vault.sh public` prints the DKIM value).
- [ ] A contact-form message from the live site lands in a real inbox, not the spam folder,
      with SPF, DKIM and DMARC passing.
- [ ] An unhandled error produces an email. `manage.py test_error_report` sends one on
      demand.

## Backups and upkeep

- [ ] `backup.yml` installed the nightly copy of `/data` to the NAS, and it has run
      unattended for several nights.
- [ ] Retention keeps the most recent 14 copies, and older ones are being pruned.
- [ ] A restore drill against real data: `restore.yml` on a scratch machine, with the
      content and a client gallery's password intact afterwards.
- [ ] `update.yml` has been run against the real server, and the site was healthy
      afterwards.
- [ ] An uptime check on `https://lauridsen-fotos.dk/healthz` alerts somewhere it will be
      seen. Proven by stopping the stack and receiving the alert.
- [ ] `expire_galleries` and `purge_tombstoned_galleries` seen in the logs to run on their
      schedule, with a real gallery expiring and its files leaving disk.
- [ ] The vault password is in a password manager that is itself backed up. Losing it means
      regenerating every secret.

## Content

- [ ] At least one portfolio category with a real album, About and Contact filled in, and
      pricing packages showing real prices.
- [ ] Everything published has both Danish and English filled in.
- [ ] One client gallery created, shared and downloaded end to end, including the expiry.
- [x] `robots.txt` and `sitemap.xml` are correct on the live domain, with no client gallery
      in either.
- [ ] A new album published through the admin without help. This is the real test.

## The release

- [ ] Tagged `v1.0.0` with `scripts/release.sh`.

---

## After 1.0.0

Good ideas, none of them blocking, roughly in the order they are likely to become worth
doing.

- **Cookie notice and privacy policy.** The site sets only strictly necessary cookies
  (session, CSRF, language), which need no consent banner under EU rules. That changes the
  day analytics arrive, and a privacy policy is worth having for a business handling client
  photographs.
- **Accessibility pass.** Keyboard navigation, visible focus states, colour contrast and
  alt-text discipline in the admin. Partly there.
- **A backup copy somewhere else.** The server and the NAS are in the same building
  ([ADR 0013](docs/decisions/0013-the-server-is-at-home.md)).
- **No root process in the cron container.** Its PID 1 is the cron daemon, which must be
  root to switch to the application's user for each job. `supercronic` would remove that.
- **Dead-man's-switch on the scheduled jobs.** Detects the expiry job silently not running,
  the one failure that stays invisible until a client's photographs outlive their expiry
  date.
- **restic or borg backups.** Deduplicated and encrypted at rest. Worth it when `/data`
  grows large enough that full nightly copies get expensive.
- **CI that deploys.** A pipeline calls `deploy.yml` instead of a person, so the deployment
  logic does not move (`architecture.md` §10).
- **A staging server.** The same playbooks with a second inventory. Worth it the first time
  an upgrade needs rehearsing on something longer-lived than `scripts/vm.sh`.
- **Cloudflare Turnstile.** Only if the honeypot and rate limit stop being enough.
- **Image pipeline tuning.** AVIF or WebP derivatives and `srcset`, if page weight becomes a
  problem on mobile connections.

Not planned, per `functional_design.md` §10: e-commerce, print ordering, online payments,
visitor accounts, and comments on timeline entries.
