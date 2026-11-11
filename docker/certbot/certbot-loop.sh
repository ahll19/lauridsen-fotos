#!/bin/sh
#
# Obtain a Let's Encrypt certificate, keep it renewed, and keep nginx able to start.
#
#   certbot-loop.sh            the long-running loop (the container's command)
#   certbot-loop.sh activate   copy the current certificate to where nginx reads it
#
# nginx will not start without a certificate, and Let's Encrypt will not issue one until
# nginx is answering on port 80. This breaks the circle: a self-signed placeholder goes in
# first so nginx can start, the real certificate replaces it as soon as it is issued, and
# nginx notices the file change and reloads (docker/nginx/reload-on-cert-change.sh).
#
# nginx reads /etc/letsencrypt/active/, a copy this script maintains, rather than
# certbot's own live/ directory — so there is always something there to read.
set -eu

: "${CERT_DOMAINS:?comma-separated list of names for the certificate}"
ACTIVE=/etc/letsencrypt/active
WEBROOT=/var/www/certbot
PRIMARY=${CERT_DOMAINS%%,*}
LIVE=/etc/letsencrypt/live/$PRIMARY

log() { printf '[certbot] %s\n' "$*"; }

activate() {
    mkdir -p "$ACTIVE"
    # Written beside the target and renamed, so nginx never reads half a file.
    cp -L "$LIVE/fullchain.pem" "$ACTIVE/fullchain.pem.new"
    cp -L "$LIVE/privkey.pem" "$ACTIVE/privkey.pem.new"
    chmod 600 "$ACTIVE/privkey.pem.new"
    mv "$ACTIVE/privkey.pem.new" "$ACTIVE/privkey.pem"
    mv "$ACTIVE/fullchain.pem.new" "$ACTIVE/fullchain.pem"
    rm -f "$ACTIVE/PLACEHOLDER"
    log "certificate for $PRIMARY is in place"
}

if [ "${1:-}" = "activate" ]; then
    activate
    exit 0
fi

if [ ! -s "$ACTIVE/fullchain.pem" ]; then
    log "no certificate yet; writing a self-signed placeholder so nginx can start"
    mkdir -p "$ACTIVE"
    openssl req -x509 -nodes -newkey rsa:2048 -days 7 -subj "/CN=$PRIMARY" \
        -keyout "$ACTIVE/privkey.pem" -out "$ACTIVE/fullchain.pem" 2>/dev/null
    chmod 600 "$ACTIVE/privkey.pem"
    touch "$ACTIVE/PLACEHOLDER"
fi

# A certificate from an earlier run that was never copied across — a restore, say.
if [ -e "$ACTIVE/PLACEHOLDER" ] && [ -s "$LIVE/fullchain.pem" ]; then
    activate
fi

# Bounded, because certbot holds a lock while it runs: one attempt stuck on an unreachable
# server would otherwise block every later one, and renewal would stop without an error.
run_certbot() { timeout "${CERTBOT_TIMEOUT:-600}" certbot "$@"; }

obtain() {
    if [ "${LETSENCRYPT_AGREE_TOS:-0}" != "1" ]; then
        log "LETSENCRYPT_AGREE_TOS is not 1; not requesting a certificate"
        return 1
    fi
    set -- certonly --webroot -w "$WEBROOT" --non-interactive --agree-tos \
        --cert-name "$PRIMARY" -d "$CERT_DOMAINS"
    if [ -n "${LETSENCRYPT_EMAIL:-}" ]; then
        set -- "$@" --email "$LETSENCRYPT_EMAIL" --no-eff-email
    else
        set -- "$@" --register-unsafely-without-email
    fi
    [ -n "${CERTBOT_SERVER:-}" ] && set -- "$@" --server "$CERTBOT_SERVER"
    # shellcheck disable=SC2086  # deliberately split: a list of extra flags
    run_certbot "$@" ${CERTBOT_EXTRA_ARGS:-} && activate
}

log "waiting for nginx to answer on port 80"
tries=0
until nc -z "${NGINX_HOST:-reverse-proxy}" 80 2>/dev/null; do
    tries=$((tries + 1))
    [ "$tries" -lt 60 ] || { log "nginx never came up"; exit 1; }
    sleep 5
done

while :; do
    if [ ! -s "$LIVE/fullchain.pem" ]; then
        # A failed attempt is retried slowly. Let's Encrypt allows five failures an hour
        # for a name, and a tight loop against a DNS record that is not there yet would
        # spend them all and lock the name out.
        obtain || { log "no certificate obtained; trying again in ${CERTBOT_RETRY_INTERVAL:-900}s"
                    sleep "${CERTBOT_RETRY_INTERVAL:-900}"; continue; }
    else
        # Does nothing unless a certificate is within thirty days of expiring.
        # shellcheck disable=SC2086
        run_certbot renew --non-interactive --deploy-hook "$0 activate" ${CERTBOT_EXTRA_ARGS:-} \
            || log "renewal run failed; it will be tried again"
    fi
    sleep "${CERTBOT_RENEW_INTERVAL:-43200}"
done
