# 0008. TLS ends at a reverse proxy in front of the server

- **Date**: 2026-11-12
- **Status**: Accepted
- **Affects**: `architecture.md` §1, §3, §4 and §7. Supersedes [0006](0006-certbot-keeps-a-certificate-where-nginx-reads-it.md)

## Context

The design had nginx inside the stack terminate TLS, with a `certbot` container obtaining
and renewing the certificate ([ADR 0006](0006-certbot-keeps-a-certificate-where-nginx-reads-it.md)).
Certificates are now handled by a reverse proxy Anders runs in front of the server, outside
this repository. Two layers each holding a certificate for the same name would be two
renewals to keep working for no gain.

## Decision

The stack serves plain HTTP on port 80 and holds no certificate. There is no `certbot`
service, no HTTPS server block, and nothing in the inventory about Let's Encrypt.

The proxy in front terminates TLS and forwards to the server's port 80. It must:

- pass `Host` through unchanged,
- set `X-Forwarded-Proto: https`,
- append the visitor's address to `X-Forwarded-For`,
- accept request bodies up to `MAX_UPLOAD_SIZE` (100 MB) and wait up to five minutes, for
  photograph uploads.

nginx passes `X-Forwarded-Proto` on to Django, which still decides the site is served over
HTTPS: cookies are marked Secure, HSTS is sent, and a request the proxy marks as plain
HTTP is redirected. `TRUSTED_PROXY_COUNT` is 2 on the server, for the proxy and nginx.

Because those headers decide security behaviour, nginx accepts connections only from the
addresses in `upstream_proxy_addresses` and refuses everyone else with 403. The check is in
nginx rather than `ufw`, because Docker publishes ports past `ufw` and a firewall rule there
would protect nothing.

## Consequences

The server no longer needs port 443 open, and nothing on it can fail to renew.

The site's availability now depends on a machine this repository does not describe. If the
proxy is down, so is the site, and nothing here will notice — the uptime check has to go
through the proxy to mean anything.

With `upstream_proxy_addresses` empty, anyone who finds the server's address can reach
nginx directly, claim any visitor address and so dodge the rate limits. The deploy prints a
warning when it is empty. The Hetzner Cloud Firewall can enforce the same restriction a
layer further out, and should.

The rehearsal plays the proxy with Caddy on the second disposable machine, using a
certificate from Caddy's internal CA.

Putting TLS back on the server means reverting to ADR 0006, whose code is in git history
before this record.
