# 0004. Deliver mail directly rather than through a smarthost

- **Date**: 2026-09-14
- **Status**: Accepted
- **Affects**: [architecture.md](../../architecture.md) §3, §4; [ROADMAP.md](../../ROADMAP.md) 0.3.0, 0.5.0

## Context

The site sends two kinds of mail, both to the owner and neither to a customer: a copy of
each contact-form submission, and Django's unhandled-error reports. That is perhaps a few
dozen messages a year. Until now they have gone to Mailpit, which captures mail and shows
it in a browser instead of delivering it, and 0.3.0 is where a relay that actually delivers
has to be chosen.

`architecture.md` §3 left the question open, mentioning SPF, DKIM and rDNS "if the mail
relay ever needs to hand off to the public internet directly (rather than to a smarthost)".
Both options were real:

- **A smarthost** — Postmark, Mailgun, SES — means handing the message to a service that
  has already solved deliverability. Their free tiers cover this volume several times over.
  It costs an external dependency, an account, an API credential in the vault, and a third
  party holding the contents of every enquiry.
- **Direct delivery** means the relay looks up each recipient's MX record and connects to
  it. Nothing leaves the stack, but the server has to earn the right to be believed: a
  reverse DNS record matching the name it announces, an SPF record naming its address, and
  a DKIM signature whose public key is published in DNS.

The deciding consideration was ownership rather than cost. This is a site built so that one
person can rebuild it from a clone, and every other moving part already lives in the
repository and the playbooks. A transactional mail provider would be the only component
whose failure, price change, or account suspension could not be fixed from here. The
volume is also low enough that the usual argument for a provider — reputation management
across large sends — does not apply.

## Decision

The mail relay is Postfix, configured to deliver straight to recipients' MX hosts. No
`RELAYHOST` is set. Deliverability is earned through DNS: rDNS on the VPS, an SPF record,
and DKIM signing with keys mounted into the container.

The relay accepts mail only from the Docker network and only with a sender in
`MAIL_SENDER_DOMAIN`. It publishes no ports at all.

Because Postfix and Mailpit have nothing in common beyond speaking SMTP, they are two
compose services selected by profile rather than one service with a swapped image — see
the Consequences below.

## Consequences

**The proof splits across two milestones.** Whether the application can hand a message to
the relay is a property of this repository and is checked locally by `scripts/prodcheck.sh`.
Whether the message arrives is a property of an IP address and a DNS zone, neither of which
exists yet, and cannot be checked locally at all: residential ISPs block outbound port 25,
and there is no rDNS to match. The relay is therefore built in 0.3.0 and the first real
delivery is proven in 0.5.0, alongside DNS and certificates.

**Three DNS records become load-bearing.** rDNS, SPF and DKIM have to be right before the
first message is sent in anger, and the failure they produce is silent: mail is accepted by
the receiving server and filed as spam. 0.5.0's definition of done therefore requires a
message observed arriving in a real inbox, not merely sent.

**Hetzner blocks outbound port 25 by default** on new accounts and unblocks it on request.
Nothing works until that request is made, and the symptom is a queue that quietly fills up.

**Revisiting is cheap.** Setting `RELAYHOST` with credentials turns this into a smarthost
configuration without touching the application, which reads only `EMAIL_HOST` and
`EMAIL_PORT`. If deliverability turns out to be a running maintenance cost rather than a
one-off setup, switching is a change to the vault and one environment variable. Prefer that
over fighting a reputation problem.

**Two services instead of one variable.** The roadmap originally expected the swap to
happen behind the existing `MAIL_RELAY_IMAGE` variable. That turned out not to work:
Mailpit's message cap and web UI mean nothing to Postfix, and Postfix's hostname, sender
restriction, DKIM keys and queue volume mean nothing to Mailpit, so one service definition
would have been mostly settings inert for whichever image was running. Worse, the shared
variable failed dangerously — an `.env` still carrying the old Mailpit value started
Mailpit under the name `postfix`, a relay that accepts every message and delivers none of
them, with nothing in the logs to say so. The images are now named per service
(`MAILPIT_IMAGE`, `POSTFIX_IMAGE`), so a stale value is inert rather than wrong.
