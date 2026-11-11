# Architecture — Infrastructure & Operational Design

This document describes **how the hosting environment is built and operated**: the server,
the network, the container topology, and how backups/monitoring/maintenance are carried out.
It deliberately stays one level above any specific application — everything here is written
so it would still make sense if "the application" were swapped for a different single-app
project of similar size. The application-specific technical decisions (data model, how each
functional requirement is implemented) live in `technical_design.md`.

## 1. Overview

A single VPS runs the entire stack as a set of Docker Compose services behind one reverse
proxy. There is no orchestration platform (no Kubernetes, no multi-node setup) — the traffic
volume doesn't warrant it, and a single well-backed-up host is easier to reason about and
operate than a distributed system, for one owner-operator.

```
Internet
   │
   ▼
[ VPS: public IP, firewall ]
   │  ports 80/443 (and 25/587 if mail is exposed externally)
   ▼
[ reverse-proxy container: nginx + certbot ]
   │  internal Docker network only
   ├──▶ [ app container: gunicorn + application code ]
   ├──▶ [ app-cron container: same image, scheduled jobs ]
   └──▶ [ mail-relay container: outbound-only SMTP relay ]
              │
              ▼
        (delivers to the owner's real mailbox, wherever that lives)

[ /data ] ── bind-mounted host directory ── shared by app + app-cron containers
   │
   ▼ (off-host, scheduled)
[ backup target: NAS or separate provider storage ]
```

Only the reverse proxy is reachable from the internet. Every other container talks to it (or
to each other) over the internal Docker network and is never directly exposed.

## 2. Host (VPS)

- **Sizing**: a single VPS with ~4–8 GB RAM and ~200 GB disk is comfortably enough for this
  class of application (low traffic, image-heavy storage, no heavy compute). Sizing is a
  knob to revisit later if traffic or storage needs grow — it isn't an architectural
  commitment.
- **OS**: Debian 12 (bookworm) — Docker's most-tested base OS family, a minimal footprint,
  and a long security-patch lifetime for a host that's meant to be set up once and left
  alone. Ubuntu LTS would work equally well if preferred; Debian is simply the default
  chosen here.
- **Base packages**: Docker Engine + the Docker Compose plugin are the only real
  dependencies on the host itself. Everything application-specific lives inside containers,
  so the host stays thin and easy to rebuild from scratch if it ever needs replacing.
  Configuration management (see §10) adds nothing here — it works over SSH and installs no
  agent, so this remains the complete list.

## 3. Networking

- **Public entry points**: only ports 80 and 443 need to be open to the world (plus a mail
  submission port only if the relay ever needs to accept mail from outside the Docker
  network, which it shouldn't in the current design — see §6).
- **Firewall**: `ufw` at the host level denies everything by default and explicitly allows
  80/443 (and SSH, restricted as below). Since the VPS is hosted at Hetzner, Hetzner's own
  Cloud Firewall sits in front of it as a second, free layer of defense-in-depth — belt and
  suspenders, not a substitute for `ufw`. Every other container port is only reachable over
  the internal Docker network, never published to the host's public interface.
- **DNS**: the domain's A/AAAA record points at the VPS's public IP. If the mail relay ever
  needs to hand off to the public internet directly (rather than to a smarthost), matching
  SPF/DKIM/rDNS records are set up on that same domain — good practice regardless of which
  mailbox ultimately receives the mail.
- **TLS termination**: happens once, at the reverse proxy. Nothing behind it needs to know
  about certificates.

## 4. Containerized setup

Everything runs as Docker Compose services on one internal network:

| Service         | Role                                                              |
| ---------------- | ------------------------------------------------------------------ |
| `reverse-proxy`  | nginx; TLS termination; the only container with published ports.  |
| `certbot`        | Requests/renews Let's Encrypt certificates on a schedule; shares a volume with the reverse proxy so renewed certs are picked up without manual steps. |
| `app`            | The application server (e.g. gunicorn) serving requests, built from the application's own image. |
| `app-cron`       | The **same image** as `app`, but run with a different entrypoint/command dedicated to scheduled jobs (see §5). Sharing the image avoids drift between "what runs the app" and "what runs its scheduled jobs." |
| `mail-relay`     | A minimal outbound-only SMTP relay container. Accepts mail only from the internal Docker network and delivers it onward; never accepts connections from the public internet. |

Each service is a separate container so a restart, redeploy, or resource limit on one never
touches the others — e.g. redeploying the app doesn't restart the mail relay, and the cron
container can be paused independently for maintenance without taking the site down.

## 5. Storage

A single host directory (e.g. `/data`) is bind-mounted into both `app` and `app-cron`. It
holds everything that isn't disposable: the database file and all uploaded media. Anything
derived/regenerable (cached thumbnails, generated web-sized variants) lives in its own
subpath so it can be excluded from backups and safely wiped/rebuilt without data loss.
Container processes run as a non-root user with ownership scoped to this directory only —
the containers have no reason to write anywhere else on the host.

## 6. Scheduled jobs

Rather than a separate scheduler service, scheduled work (e.g. expiring time-limited content,
periodic housekeeping) is scheduled by a standard `cron` daemon running inside the
`app-cron` container itself. `docker compose up` brings up a fully self-scheduling stack —
nothing needs to be configured on the host for this to work, which also means the schedule
travels with the container definition rather than living separately in host state. No
bespoke job queue or scheduler framework is introduced for this.

## 7. TLS & certificates

Certificates are obtained and renewed by the `certbot` container against Let's Encrypt using
the HTTP-01 challenge, served through the reverse proxy — the simplest option, and sufficient
since nothing in the functional design calls for wildcard subdomains (client galleries are
paths under the main domain, not subdomains). Renewal runs on a recurring schedule well
before expiry, and the reverse proxy is signaled to reload once a renewal succeeds. If a
wildcard cert is ever needed later (e.g. a `*.domain` scheme), that would mean switching to
the DNS-01 challenge against the domain's DNS provider — worth flagging now only because it
would be a deliberate later change, not the default. How the certificate reaches nginx, and how
nginx starts before there is one, is in
[docs/decisions/0006-certbot-keeps-a-certificate-where-nginx-reads-it.md](docs/decisions/0006-certbot-keeps-a-certificate-where-nginx-reads-it.md).

## 8. Backups

- **What's backed up**: the entire persistent data directory (database + original media),
  excluding the disposable derived/cache subpath.
- **Where**: the VPS is hosted at Hetzner, so backups target the owner's home NAS —
  independent of Hetzner, so a Hetzner-side outage or account issue can't take out both the
  live system and its backups.
- **How**: a nightly `rsync` of the data directory to the NAS. A later upgrade to a
  snapshotting/deduplicating tool (`restic` or `borg`) remains an option if point-in-time
  recovery or at-rest encryption on the NAS becomes a priority, but isn't part of the initial
  setup.
- **Retention**: a flat rotation of the most recent 14 nightly copies (~2 weeks of recovery
  window) is kept on the NAS; older copies are pruned automatically. This number is easy to
  change later — flag if 2 weeks isn't the right window.

## 9. Monitoring & alerting

Kept proportionate to a low-traffic, single-owner site — no heavyweight observability stack:

- **Reachability**: an external uptime-checking service (e.g. UptimeRobot) periodically
  requests the public site and alerts (push/email) if it goes down. No extra container to
  run for this — it's the one piece of monitoring that deliberately lives outside the stack.
- **Application errors**: the application's own error-reporting is wired straight into the
  mail relay already running (§4/§6) — sending the site owner an email whenever an unhandled
  error occurs, without needing a separate error-tracking service.
- **Host/container health**: no dedicated dashboard — `docker stats` and `docker compose
  logs` are checked manually if something seems off. At this traffic level a standing
  metrics/alerting pipeline would be overhead without a corresponding benefit.
- Deliberately out of scope: a dead-man's-switch check on the cron job (i.e. detecting that
  scheduled cleanup silently stopped running). This is a reasonable thing to add later if the
  expiry job's reliability ever becomes a concern, but isn't part of the initial setup.

## 10. Updates & maintenance

- **Configuration management**: the host is not configured by hand. Everything from the bare
  OS upwards — packages, users, SSH hardening, firewall rules, the application's directory
  layout and its environment file — is described as Ansible playbooks kept in this
  repository, and applied from the operator's own machine over SSH. Ansible is agentless, so
  this adds no running software to the host (§2). The point is that the server is
  reproducible rather than a pet: if it is lost or has to be moved to a different provider,
  it is rebuilt by re-running the playbooks against a fresh machine, not by remembering what
  was once typed into it. Secrets the playbooks need are held in an encrypted vault in the
  repository, so a clone plus one vault password is enough to rebuild — see
  [docs/decisions/0002-manage-the-host-with-ansible.md](docs/decisions/0002-manage-the-host-with-ansible.md).
- **OS security patches**: automatic security-only updates on the host (e.g.
  `unattended-upgrades` on Debian/Ubuntu), installed by the provisioning playbook, so the
  host doesn't silently drift out of date between maintenance windows.
- **Container images**: versions are pinned explicitly (no floating `latest` tags in
  production) and bumped deliberately as part of a maintenance pass, then redeployed —
  rather than auto-updating containers in place, which trades predictability for
  convenience in a way that isn't worth it for a small, infrequently-touched stack.
- **Application dependencies**: kept current via periodic manual review (checking for
  Django/library security releases during a maintenance pass) rather than an automated
  PR-based update bot — proportionate for a single-maintainer project; easy to switch to
  Dependabot/Renovate later if that manual cadence ever slips.
- **Deployment mechanism**: the image is built directly on the VPS (the code is shipped to
  it rather than pulled — see
  [docs/decisions/0005-ship-releases-from-the-operators-machine.md](docs/decisions/0005-ship-releases-from-the-operators-machine.md) —
  then `docker build` and `docker compose up -d`) rather than built elsewhere and pushed to a
  container registry — one less moving part and no registry account needed while there's no
  CI pipeline yet. That sequence is itself a playbook rather than a set of commands to run by
  hand, so a deployment is one invocation that ends by checking the site answers. Wiring this
  into a CI/CD tool (e.g. Jenkins) later, with a registry in between, is a natural upgrade
  that doesn't require changing anything else about the architecture — CI would call the same
  playbook, and the deployment step stays a thin, replaceable layer on top of "get new code
  onto the host, restart the affected services."

## 11. Security baseline

- SSH access is key-only (no password auth), on a firewall-restricted basis.
- The firewall denies all inbound traffic by default; only the reverse proxy's ports (and
  restricted SSH) are opened.
- Containers run as non-root users wherever the base image supports it.
- Secrets (database credentials if any, mail relay credentials, application secret keys) are
  injected via environment variables / an untracked `.env` file — never committed to version
  control in plaintext. The host's `.env` is rendered by the configuration-management layer
  (§10) from an encrypted vault, so the values exist on the host and in the vault, and
  nowhere else.
- The mail relay only ever accepts connections from the internal Docker network, never from
  the public internet, removing an entire class of open-relay/abuse risk.

## Next step

`technical_design.md` builds on this architecture to describe how the application itself
(data model, request handling, background jobs) implements each requirement from
`functional_design.md`.
