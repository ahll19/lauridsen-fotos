#!/bin/sh
#
# Turn UPSTREAM_PROXY_ADDRESSES into nginx `allow` rules.
#
# Run by the nginx image at container start, like everything in /docker-entrypoint.d/.
# The list is space-separated addresses or CIDR ranges: the reverse proxy in front, as this
# server sees it connect. Empty means anyone may connect, which is right on a laptop.
#
# This is the restriction that holds. Docker publishes ports past the host firewall, so a
# ufw rule on port 80 would look like protection and be none.
set -eu

out=/etc/nginx/upstream-allow.conf

if [ -z "${UPSTREAM_PROXY_ADDRESSES:-}" ]; then
    echo "allow all;" >"$out"
    echo "upstream-allow: UPSTREAM_PROXY_ADDRESSES is empty; anyone may connect"
    exit 0
fi

: >"$out"
for address in $UPSTREAM_PROXY_ADDRESSES; do
    printf 'allow %s;\n' "$address" >>"$out"
done
echo "upstream-allow: only $UPSTREAM_PROXY_ADDRESSES may connect"
