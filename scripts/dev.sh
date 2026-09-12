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
        require_env
        echo "==> Building and starting"
        compose up -d --build
        echo "==> Waiting for the site to answer"
        load_env
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
        compose down
        ;;

    reset)
        load_env
        echo "This deletes ${DATA_DIR:-./data} — the database and every uploaded photograph."
        read -r -p "Type 'yes' to continue: " confirm
        [[ "$confirm" == "yes" ]] || { echo "Cancelled."; exit 1; }
        compose down -v
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
