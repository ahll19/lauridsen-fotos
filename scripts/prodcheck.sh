#!/usr/bin/env bash
#
# Run the stack the way production runs it, on this machine, and check it.
#
# Production is a genuinely different code path, not just a different flag: static files
# are served under content-hashed names through a manifest, error pages come from
# templates instead of Django's debug traceback, and the security middleware stops being
# lenient. Every one of those has failed for someone on the first deploy. This finds them
# here instead, where the cost is a restart.
#
#   scripts/prodcheck.sh          check, then put development mode back
#   scripts/prodcheck.sh --keep   check, and leave the stack in production mode
#
# --keep is for looking around by hand: the error pages, the admin over a Secure-cookie
# configuration, a form submission. `scripts/dev.sh up` returns to development whenever
# you are done. Without it the stack is left the way it was found, because forgetting a
# machine is in production mode is how an afternoon disappears wondering why CSS edits do
# nothing.
#
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

KEEP=0
case "${1:-}" in
    --keep) KEEP=1 ;;
    "")     ;;
    *)      echo "usage: scripts/prodcheck.sh [--keep]" >&2; exit 2 ;;
esac

bold=$(tput bold 2>/dev/null || true)
red=$(tput setaf 1 2>/dev/null || true)
green=$(tput setaf 2 2>/dev/null || true)
reset=$(tput sgr0 2>/dev/null || true)

FAILED=0
step() { printf '\n%s==> %s%s\n' "$bold" "$1" "$reset"; }
ok()   { printf '    %s✓%s %s\n' "$green" "$reset" "$1"; }
fail() { printf '    %s✗%s %s\n' "$red" "$reset" "$1"; FAILED=1; }

# The generated production-mode environment. Kept beside .env rather than in /tmp so it is
# obvious what it is if it ever survives a crash, and gitignored alongside .env.
PROD_ENV=.env.prodcheck

if [[ ! -f .env ]]; then
    echo "No .env found. Run: cp .env.example .env" >&2
    exit 1
fi

# Runs on every exit path — a passed run, a failed check, a Ctrl-C — so the machine is never
# left in production mode by accident. With --keep it says where things stand instead.
restore() {
    local status=$?
    if (( KEEP )); then
        step "Leaving the stack in production mode (--keep)"
        printf '    The site is at http://localhost:%s in the configuration the VPS will\n' "${HTTP_PORT:-8080}"
        printf '    use. Static files are content-hashed, errors are pages rather than\n'
        printf '    tracebacks, and %s holds the settings.\n\n' "$PROD_ENV"
        printf '    Back to development:  scripts/dev.sh up\n'
        exit "$status"
    fi
    step "Restoring the development stack"
    # Unset before anything else. These are exported below and a subshell inherits them,
    # so leaving APP_ENV_FILE pointing at the file just deleted would bring the stack back
    # up with no environment file at all — which, with DJANGO_DEBUG then defaulting off
    # and the secret key defaulting to the placeholder, is a refusal to start and a
    # container restart loop.
    unset APP_ENV_FILE STATIC_CACHE_CONTROL DJANGO_DEBUG DJANGO_SERVE_OVER_HTTPS
    rm -f "$PROD_ENV"
    ( set -a; . ./.env; set +a
      export COMPOSE_PROFILES="${COMPOSE_PROFILES:-dev}"
      docker compose up -d --remove-orphans >/dev/null 2>&1 ) || true
    # Changing the env file recreates the app container, so give it the same chance to
    # come up that the start did. Without this the restore reports a failure every time
    # and sends you looking for a problem that fixed itself while you read the message.
    for _ in $(seq 1 30); do
        curl -fsS "http://localhost:${HTTP_PORT:-8080}/healthz" >/dev/null 2>&1 && break
        sleep 2
    done
    if curl -fsS "http://localhost:${HTTP_PORT:-8080}/healthz" >/dev/null 2>&1; then
        ok "back on .env"
    else
        # Worth saying out loud: a failed restore leaves the machine unusable, and the
        # reason will not be obvious from whatever check failed first.
        fail "the development stack did not come back — run scripts/dev.sh up"
        status=1
    fi
    exit "$status"
}
trap restore EXIT

# --- The production-mode environment ----------------------------------------
# Derived from .env so it inherits the ports and paths this machine actually uses, with
# only the settings that differ in production replaced.
step "Rendering $PROD_ENV"

SECRET=$(python3 -c "import secrets; print(secrets.token_urlsafe(64))")
python3 - "$PROD_ENV" "$SECRET" <<'PY'
import re
import sys

target, secret = sys.argv[1], sys.argv[2]
text = open(".env").read()

overrides = {
    "DJANGO_DEBUG": "0",
    # Ephemeral and thrown away with the file. A real one lives in the vault.
    "DJANGO_SECRET_KEY": secret,
    # nginx may only promise immutability for filenames carrying a content hash, which is
    # exactly what DJANGO_DEBUG=0 produces. The two belong to each other.
    "STATIC_CACHE_CONTROL": '"public, max-age=2592000, immutable"',
    # The one place this run is deliberately unlike production: there is no certificate
    # here, so the site answers on http://localhost. See .env.example.
    "DJANGO_SERVE_OVER_HTTPS": "0",
}
for key, value in overrides.items():
    line = f"{key}={value}"
    text, count = re.subn(rf"^{key}=.*$", line.replace("\\", "\\\\"), text, flags=re.M)
    if not count:
        text += f"\n{line}\n"
open(target, "w").write(text)
PY
ok "production settings, development ports"

# --- Bring it up -------------------------------------------------------------
step "Starting in production mode"

set -a
# shellcheck source=/dev/null
. ./.env
set +a
export COMPOSE_PROFILES="${COMPOSE_PROFILES:-dev}"
export APP_ENV_FILE="$PROD_ENV"
export STATIC_CACHE_CONTROL="public, max-age=2592000, immutable"
PORT="${HTTP_PORT:-8080}"
BASE="http://localhost:${PORT}"

docker compose up -d >/dev/null
for _ in $(seq 1 60); do
    curl -fsS "${BASE}/healthz" >/dev/null 2>&1 && break
    sleep 2
done
if ! curl -fsS "${BASE}/healthz" >/dev/null 2>&1; then
    fail "the site did not come up"
    docker compose logs --tail 40 app >&2
    exit 1
fi
ok "answering on ${BASE}"

# --- Django's own deployment checklist ---------------------------------------
# Run with DJANGO_SERVE_OVER_HTTPS forced back on, so what is checked is the posture the
# VPS will have rather than the one this machine is running. Without that, the check would
# report the three settings prodcheck deliberately relaxed and be no use.
step "manage.py check --deploy"

if output=$(docker compose exec -T -e DJANGO_SERVE_OVER_HTTPS=1 app \
        python manage.py check --deploy 2>&1); then
    if grep -q "no issues" <<<"$output"; then
        ok "no issues"
    else
        fail "warnings to read and decide about:"
        sed 's/^/        /' <<<"$output"
    fi
else
    fail "check --deploy reported errors:"
    sed 's/^/        /' <<<"$output"
fi

# --- Static assets -----------------------------------------------------------
# ManifestStaticFilesStorage is where production most often breaks: a {% static %} path
# that does not resolve raises at render time rather than serving a 404, so a page that
# worked all through development returns a 500 on the first deploy.
step "Hashed static assets"

if docker compose exec -T app test -f /srv/static/staticfiles.json; then
    ok "staticfiles.json written"
else
    fail "no manifest — collectstatic did not run with DJANGO_DEBUG=0"
fi

home=$(curl -fsS "$BASE/")
hashed=$(grep -oE '/static/[^"]*\.[0-9a-f]{12}\.[a-z]+' <<<"$home" | head -1 || true)
if [[ -n "$hashed" ]]; then
    ok "templates reference hashed names (${hashed##*/})"
    code=$(curl -s -o /dev/null -w '%{http_code}' "${BASE}${hashed}")
    if [[ "$code" == 200 ]]; then
        ok "and they are served"
    else
        fail "$hashed returned $code"
    fi
    cache=$(curl -sI "${BASE}${hashed}" | tr -d '\r' | grep -i '^cache-control:' || true)
    if grep -qi immutable <<<"$cache"; then
        ok "cached ${cache#*: }"
    else
        # Only a hashed name may be called immutable, and only then. Saying so about a
        # name that can change means an edited stylesheet no reload will refresh.
        fail "hashed assets are not marked immutable: ${cache:-no Cache-Control header}"
    fi
else
    fail "no content-hashed asset on the front page"
fi

# --- Every page -------------------------------------------------------------
step "Crawling every reachable page"

if output=$(python3 scripts/crawl.py "$BASE/" 2>&1); then
    ok "$output"
else
    fail "non-200 responses:"
    sed 's/^/        /' <<<"$output"
fi

# --- Error pages -------------------------------------------------------------
# With DJANGO_DEBUG=0 these come from templates. Django falls back to a bare unstyled
# English page if a template is missing or raises, so checking for the site's own chrome
# is what distinguishes "our 404" from "Django's 404".
step "Error pages"

heading() { sed -n 's/.*error__title">\([^<]*\)<.*/\1/p' | head -1; }

for path in /no-such-page/ /en/no-such-page/; do
    body=$(curl -s "${BASE}${path}")
    code=$(curl -s -o /dev/null -w '%{http_code}' "${BASE}${path}")
    if [[ "$code" == 404 ]] && grep -q 'site-header' <<<"$body"; then
        ok "$path — \"$(heading <<<"$body")\""
    else
        fail "$path returned $code without the site's chrome"
    fi
done

# Compared rather than matched against known wording, so rewriting the copy doesn't break
# the check. What must not happen is both languages rendering the same text, which is what
# a missing or stale .mo file looks like: silently English everywhere.
danish=$(curl -s "${BASE}/no-such-page/" | heading)
english=$(curl -s "${BASE}/en/no-such-page/" | heading)
if [[ -n "$danish" && "$danish" != "$english" ]]; then
    ok "translated — the two languages differ"
else
    fail "both languages render \"$english\" — compilemessages has not run"
fi

# The 500 template is rendered by Django with an empty context and no context processors,
# so anything it inherits or looks up would raise a second exception inside the handler
# for the first. Rendering it the same way here is the only honest test of that.
# Through manage.py, so Django is set up — render() with no arguments is then exactly what
# django.views.defaults.server_error does.
if output=$(docker compose exec -T app python manage.py shell -v 0 -c "
from django.template.loader import get_template
html = get_template('500.html').render()
assert '500' in html, 'the rendered page does not mention its status'
print('rendered', len(html), 'characters')
" 2>&1); then
    ok "500.html renders with no context (${output})"
else
    fail "500.html depends on a context it will not be given:"
    sed 's/^/        /' <<<"$output" | tail -5
fi

# --- Mail --------------------------------------------------------------------
step "Mail relay"

# Which relay *should* be running, decided by the profile rather than by looking. Both can
# be up at once — switching COMPOSE_PROFILES starts the new one without stopping the old —
# and asking "which relay is running" then gets two answers and matches neither.
case "${COMPOSE_PROFILES:-dev}" in
    *prod*) relay=postfix ;;
    *)      relay=mailpit ;;
esac

if ! docker compose ps --services --filter status=running | grep -qx "$relay"; then
    fail "COMPOSE_PROFILES selects $relay, but it is not running"
    relay=none
fi

case "$relay" in
    mailpit)
        ok "mailpit — captures mail instead of sending it"
        ;;
    postfix)
        ok "postfix — delivering straight to recipients (ADR 0004)"
        # Checked before the probe below, because it is the likeliest thing to be wrong and
        # the probe's failure would not explain it. The relay only sends as
        # MAIL_SENDER_DOMAIN; if the address the site sends *from* is on some other domain,
        # every message the site ever sends is refused — and the only symptom is a contact
        # form that says it sent something.
        from_domain="${DEFAULT_FROM_EMAIL##*@}"
        if [[ "$from_domain" == "${MAIL_SENDER_DOMAIN:-}" ]]; then
            ok "DEFAULT_FROM_EMAIL is on the domain the relay may send as"
        else
            fail "DEFAULT_FROM_EMAIL is @${from_domain}, but the relay only sends as @${MAIL_SENDER_DOMAIN:-<unset>}"
        fi
        # Asked of the configuration rather than proven by sending. Sending cannot answer
        # it: the only recipients safe to address from a test are domains publishing a null
        # MX record, and Postfix rejects an unreachable recipient domain *before* it
        # consults the sender policy — so a permitted and a forbidden sender come back with
        # the same error. Any recipient that would get far enough to tell them apart is a
        # real mailbox belonging to someone else. postmap queries the map directly.
        postmap() { docker compose exec -T postfix postmap -q "$1" lmdb:/etc/postfix/allowed_senders; }
        if [[ "$(postmap "${MAIL_SENDER_DOMAIN}" 2>/dev/null)" == "OK" ]] \
           && ! postmap "not-our-domain.example" >/dev/null 2>&1; then
            ok "sends as ${MAIL_SENDER_DOMAIN} and refuses any other (not an open relay)"
        else
            fail "the sender policy does not permit exactly ${MAIL_SENDER_DOMAIN}"
        fi

        # The decision in ADR 0004, asserted rather than assumed: no relayhost means each
        # message goes to the recipient's own mail server.
        if [[ -z "$(docker compose exec -T postfix postconf -nh relayhost | tr -d '[:space:]')" ]]; then
            ok "no relayhost — delivering directly, as decided"
        else
            fail "a relayhost is set; ADR 0004 says delivery is direct"
        fi
        printf '      note: whether mail actually arrives depends on rDNS, SPF and DKIM,\n'
        printf '            which are properties of the host and its DNS. Proven in 0.5.0.\n'
        ;;
esac

# --- Verdict -----------------------------------------------------------------
if (( FAILED )); then
    printf '\n%s%sPRODUCTION CHECK FAILED%s\n' "$bold" "$red" "$reset"
    exit 1
fi
printf '\n%s%sPRODUCTION CHECK PASSED%s\n' "$bold" "$green" "$reset"
