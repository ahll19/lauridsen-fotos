#!/bin/sh
#
# Reload nginx when the certificate it serves is replaced.
#
# Run by the nginx image at container start (it executes everything in
# /docker-entrypoint.d). nginx reads a certificate once, when it starts or reloads, so a
# renewed one sitting on disk does nothing until something tells nginx about it — and a
# renewal that is never picked up ends, ninety days later, in exactly the outage renewal
# exists to prevent. certbot runs in another container and cannot signal this one, so this
# watches the file instead.
set -eu

[ "${NGINX_MODE:-http}" = "https" ] || exit 0

CERT=/etc/letsencrypt/active/fullchain.pem
INTERVAL="${CERT_RELOAD_INTERVAL:-60}"

stamp() { stat -c %Y "$CERT" 2>/dev/null || echo 0; }

(
    last=$(stamp)
    while sleep "$INTERVAL"; do
        now=$(stamp)
        if [ "$now" != "$last" ]; then
            echo "[cert-watch] certificate changed; reloading nginx"
            nginx -s reload && last=$now
        fi
    done
) &
