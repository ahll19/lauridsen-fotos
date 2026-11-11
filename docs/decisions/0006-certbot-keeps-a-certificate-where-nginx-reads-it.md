# 0006. certbot keeps a certificate where nginx reads it, and nginx watches the file

- **Date**: 2026-11-11
- **Status**: Accepted
- **Affects**: `architecture.md` §7, which says the proxy "is signaled to reload"

## Context

Two problems hide in "certbot obtains the certificate and nginx is reloaded".

nginx will not start without a certificate file to read, and Let's Encrypt will not issue
one until nginx is answering the HTTP-01 challenge on port 80. On a new host each is
waiting for the other.

And certbot and nginx are separate containers. certbot cannot send nginx a signal without
being given the Docker socket, which is root on the host — a large thing to hand to the one
container whose job is talking to the internet.

## Decision

nginx reads its certificate from `/etc/letsencrypt/active/`, a copy the certbot container
maintains, rather than from certbot's own `live/` directory. If nothing is there, certbot
writes a seven-day self-signed placeholder first, so nginx can start; when the real
certificate arrives, or is renewed, certbot replaces the copy.

nginx notices by itself: a small loop in its container compares the file's modification
time every `CERT_RELOAD_INTERVAL` seconds and reloads when it changes. No socket, no signal
between containers.

Certificate requests are off until `letsencrypt_agree_tos` is set in the inventory, because
making them is accepting Let's Encrypt's subscriber agreement.

## Consequences

A new host serves the placeholder for the few seconds before the first certificate is
issued, and for as long as DNS does not point at it. A browser will warn; that is the
correct thing for it to do.

A failed issuance is retried every `CERTBOT_RETRY_INTERVAL` seconds (fifteen minutes by
default), slowly enough to stay inside Let's Encrypt's limit of five failures an hour.

The whole sequence — placeholder, issuance, renewal, reload — was rehearsed against Pebble,
Let's Encrypt's test server, on a disposable machine. What that cannot prove is anything
about the real domain's DNS.
