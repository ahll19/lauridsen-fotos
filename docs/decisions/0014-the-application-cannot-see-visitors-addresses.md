# 0014. The application cannot see visitors' addresses

- **Date**: 2026-11-13
- **Status**: Accepted
- **Affects**: technical_design.md (contact form, client galleries); [0013](0013-the-server-is-at-home.md)

## Context

Two limits count by the visitor's address: messages through the contact form, and password
attempts on a client gallery. The application takes the address from `X-Forwarded-For`,
trusting the two proxies in front of it.

On the live server every request, from inside the network or outside it, reaches the proxy
from `192.168.1.1`. The router rewrites the source of each connection it forwards, and it
has no setting to stop. So every visitor shares one address, and each limit was one
allowance for everyone: five enquiries an hour in total, and one person hammering a gallery
link could lock every client out of theirs.

Asking the browser for its address was considered and rejected. A browser can only learn
it from a third-party service, which would be told about every visitor, and a caller who
means harm can send whatever value they like.

## Decision

The limits no longer depend on the address being real.

- **Gallery passwords** are counted per gallery and address together. With one shared
  address that is per gallery, so hammering one link affects that link only.
- **The contact form** is still counted per address, and on this server
  `contact_ratelimit` is raised to `30/h` in the inventory, as a limit for the whole site.
  The honeypot remains the first defence against bots.

The address stored with a contact submission is kept, and on this server is the router's.

## Consequences

A burst of more than thirty messages in an hour refuses the next real enquiry until the
hour passes. Someone who knows a gallery's link can keep its client from unlocking it for
an hour at a time; a client who has already unlocked it is unaffected.

Nothing here needs undoing if the addresses come back, for example behind a proxy outside
the network that passes them on: the gallery limit becomes per visitor again by itself, and
`contact_ratelimit` can go back to its default.
