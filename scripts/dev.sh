#!/usr/bin/env bash
#
# The local development stack.
#
#   scripts/dev.sh up          build if needed, start everything, wait until it answers
#   scripts/dev.sh down        stop (keeps ./data)
#   scripts/dev.sh reset       stop and delete ./data — every photo and the database
#   scripts/dev.sh logs [svc]  follow logs
#   scripts/dev.sh manage ...  run a management command, e.g. manage.sh migrate
#   scripts/dev.sh seed        fill the site with demonstration content
#   scripts/dev.sh superuser   create the admin account
#   scripts/dev.sh shell       a shell in the app container
#   scripts/dev.sh cron        run both scheduled jobs once, now
#   scripts/dev.sh urls        print where everything is
#
set -euo pipefail

cd "$(git rev-parse --show-toplevel)"

compose() { docker compose "$@"; }

# For commands that mean "all of it", regardless of which relay is currently selected.
#
# Compose only acts on services whose profile is active, and a service behind an inactive
# profile is not an orphan either — so `down --remove-orphans` walks past it just the same
# and leaves it running, which then blocks the network from being removed. Asking the
# compose file which profiles it defines keeps this correct if another is ever added.
compose_all() {
    local profiles
    profiles=$(docker compose config --profiles 2>/dev/null | paste -sd, - || true)
    COMPOSE_PROFILES="${profiles:-dev}" docker compose "$@"
}

require_env() {
    if [[ ! -f .env ]]; then
        echo "==> No .env found; copying .env.example"
        cp .env.example .env
    fi
}

# shellcheck disable=SC2046  # deliberate word splitting of the env file
load_env() {
    require_env
    set -a
    # shellcheck source=/dev/null
    . ./.env
    set +a
    # The mail relay lives behind a compose profile, so an .env predating that variable
    # would start the stack with no relay at all and fail silently at the first sent
    # message. Local work always wants Mailpit.
    export COMPOSE_PROFILES="${COMPOSE_PROFILES:-dev}"
}

urls() {
    load_env
    local port="${HTTP_PORT:-8080}"
    local admin="${DJANGO_ADMIN_PATH:-studio-admin/}"
    cat <<EOF

  Site       http://localhost:${port}/
  Admin      http://localhost:${port}/${admin}
  Mail       http://localhost:${MAIL_UI_PORT:-8025}/    (every message the site sends)
  Health     http://localhost:${port}/healthz

EOF
}

case "${1:-up}" in
    up)
        # prodcheck.sh --keep advertises this command as the way back to development, so
        # clear the production-mode environment it left behind. Otherwise the file sits in
        # the repository root looking like configuration that matters.
        if [[ -f .env.prodcheck ]]; then
            echo "==> Removing .env.prodcheck (returning to development mode)"
            rm -f .env.prodcheck
        fi
        # Before the build, not after: COMPOSE_PROFILES decides which mail relay is
        # brought up, and compose reads it from the environment at that moment.
        load_env
        echo "==> Building and starting"
        # --remove-orphans so the stack converges on the compose file rather than leaving
        # containers behind from an older version of it. Renaming a service otherwise
        # leaves the old one running and holding its published port, and the new one
        # cannot start.
        compose up -d --build --remove-orphans
        echo "==> Waiting for the site to answer"
        for _ in $(seq 1 60); do
            if curl -fsS "http://localhost:${HTTP_PORT:-8080}/healthz" >/dev/null 2>&1; then
                echo "✓ Up"
                urls
                exit 0
            fi
            sleep 2
        done
        echo "✗ The site did not come up. Recent logs:" >&2
        compose logs --tail 40 app reverse-proxy >&2
        exit 1
        ;;

    down)
        load_env
        # --remove-orphans for the same reason `up` uses it: a container created by an
        # older version of the compose file is not a service any more, so plain `down`
        # walks straight past it and leaves it running.
        compose_all down --remove-orphans
        ;;

    reset)
        load_env
        echo "This deletes ${DATA_DIR:-./data} — the database and every uploaded photograph."
        read -r -p "Type 'yes' to continue: " confirm
        [[ "$confirm" == "yes" ]] || { echo "Cancelled."; exit 1; }
        # --remove-orphans matters most here. Renaming a service — which this project did
        # when the mail relay became `mailpit` and `postfix` — leaves the old container
        # running under the old name, and `down` does not touch it because the compose
        # file no longer describes it. The network then cannot be removed either, because
        # the survivor is still attached to it. A reset that leaves a container holding
        # the tree it just deleted is not a reset.
        compose_all down -v --remove-orphans
        rm -rf "${DATA_DIR:-./data}"
        echo "✓ Reset. Run scripts/dev.sh up to start again."
        ;;

    logs)
        shift
        compose logs -f "$@"
        ;;

    manage)
        shift
        compose exec app python manage.py "$@"
        ;;

    seed)
        shift
        compose exec app python manage.py seed_demo "$@"
        ;;

    superuser)
        compose exec app python manage.py createsuperuser
        ;;

    shell)
        compose exec app bash
        ;;

    cron)
        echo "==> Running scheduled jobs once (normally on the schedule in .env)"
        compose exec app-cron python manage.py expire_galleries
        compose exec app-cron python manage.py purge_tombstoned_galleries
        ;;

    urls)
        urls
        ;;

    *)
        echo "usage: scripts/dev.sh <up|down|reset|logs|manage|seed|superuser|shell|cron|urls>" >&2
        exit 1
        ;;
esac
