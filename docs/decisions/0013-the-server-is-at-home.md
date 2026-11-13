# 0013. The server is a machine at home, not a rented VPS

- **Date**: 2026-11-13
- **Status**: Accepted
- **Affects**: architecture.md §2, §3 and §8

## Context

architecture.md describes a VPS rented from Hetzner: Debian 12, a public address of its own,
Hetzner's Cloud Firewall in front, and backups going to a NAS at home so that the site and
its backups are in different places.

The site went live on something else: a virtual machine on the owner's home network, running
Debian 13. It has a private address. The router forwards the public ports to a reverse proxy
on the same network, which terminates TLS and forwards to the server
([ADR 0008](0008-tls-ends-at-a-reverse-proxy-in-front-of-the-server.md)).

## Decision

The server is that machine. The playbooks treat it as they would any Debian host, and nothing
in them is specific to a provider.

Where architecture.md says "VPS" or "Hetzner", read "the server". Three things it says do not
hold as written:

- **§2, the OS.** The server runs Debian 13. The playbooks work on 12 and 13, and the
  rehearsal machines run 13 to match.
- **§3, the firewall.** There is no provider firewall. The layers are the router, which
  forwards only to the proxy, then `ufw` and nginx's allow list on the server.
- **§8, where backups go.** The NAS is in the same building as the server. A fire, a theft
  or a power surge can take both.

## Consequences

Nothing is paid for monthly, and the server's snapshots are the hypervisor's.

The site is only as available as the home connection and its power. An uptime check from
outside matters more than it would in a data centre.

Backups no longer protect against losing the building. A copy somewhere else is on the
roadmap for after 1.0.0.

Mail leaves from a residential address. Many providers block outbound port 25 from one, and
receivers trust such addresses less. If mail cannot be delivered directly, the answer is a
smarthost, which reopens
[ADR 0004](0004-deliver-mail-directly-rather-than-through-a-smarthost.md).

Moving to a rented server later is a new inventory and a restore from backup, not a redesign.
