#!/usr/bin/env bash
#
# Shared entrypoint for both roles of this image.
#
#   entrypoint.sh web    gunicorn, after migrations and asset collection
#   entrypoint.sh cron   the cron daemon, with schedules rendered from the environment
#
set -euo pipefail

ROLE="${1:-web}"
DATA_ROOT="${DATA_ROOT:-/data}"
APP_USER=app

log() { printf '[entrypoint] %s\n' "$*"; }

# --- Writable layout on the bind mount ---------------------------------------
# Created here rather than assumed, so a fresh clone with an empty ./data works.
mkdir -p \
    "$DATA_ROOT/media/portfolio" \
    "$DATA_ROOT/media/timeline" \
    "$DATA_ROOT/media/galleries" \
    "$DATA_ROOT/cache/thumbnails"

if [[ "$(id -u)" -eq 0 ]]; then
    chown -R "$APP_USER:$APP_USER" "$DATA_ROOT" /srv/static 2>/dev/null || true
fi

as_app() {
    if [[ "$(id -u)" -eq 0 ]]; then
        runuser -u "$APP_USER" -- "$@"
    else
        "$@"
    fi
}

case "$ROLE" in
    web)
        log "Applying database migrations"
        as_app python manage.py migrate --noinput

        log "Compiling translation catalogues"
        as_app python manage.py compilemessages --ignore=.venv 2>/dev/null || \
            log "No translation catalogues to compile yet"

        # Refresh the shared volume so a rebuilt image's assets are actually served,
        # which a build-time collectstatic alone would not achieve.
        log "Collecting static assets"
        as_app python manage.py collectstatic --noinput --clear >/dev/null

        log "Starting gunicorn on :${APP_PORT:-8000}"
        gunicorn_cmd=(
            gunicorn config.wsgi:application
            --bind "0.0.0.0:${APP_PORT:-8000}"
            --workers "${GUNICORN_WORKERS:-3}"
            --timeout "${GUNICORN_TIMEOUT:-120}"
            --access-logfile -
            --error-logfile -
        )
        # exec, so gunicorn becomes PID 1 and receives docker's stop signals directly.
        if [[ "$(id -u)" -eq 0 ]]; then
            exec runuser -u "$APP_USER" -- "${gunicorn_cmd[@]}"
        else
            exec "${gunicorn_cmd[@]}"
        fi
        ;;

    cron)
        # cron starts with an empty environment, so the variables the management commands
        # need are written out and sourced by each job.
        log "Exporting environment for cron jobs"
        declare -px \
            | grep -E ' (DJANGO_|EMAIL_|GALLERY_|CONTACT_|DATA_ROOT|APP_PORT|USE_X_ACCEL|OWNER_EMAIL|SERVER_EMAIL|DEFAULT_FROM_EMAIL)' \
            > /app/cron.env || true
        chown "$APP_USER:$APP_USER" /app/cron.env
        chmod 600 /app/cron.env

        log "Rendering schedules"
        log "  expire-galleries: ${CRON_SCHEDULE_EXPIRE_GALLERIES:-0 3 * * *}"
        log "  purge-tombstones: ${CRON_SCHEDULE_PURGE_TOMBSTONES:-30 3 * * *}"
        export CRON_SCHEDULE_EXPIRE_GALLERIES="${CRON_SCHEDULE_EXPIRE_GALLERIES:-0 3 * * *}"
        export CRON_SCHEDULE_PURGE_TOMBSTONES="${CRON_SCHEDULE_PURGE_TOMBSTONES:-30 3 * * *}"
        export APP_USER
        envsubst < /usr/local/bin/crontab.template > /etc/cron.d/app-jobs
        chmod 0644 /etc/cron.d/app-jobs

        log "Starting cron daemon"
        exec cron -f -L 2
        ;;

    *)
        # Anything else is run verbatim, which is what makes `docker compose run app <cmd>`
        # and one-off management commands work. exec needs a real command, not the helper
        # function, so the privilege drop is spelled out here too.
        if [[ "$(id -u)" -eq 0 ]]; then
            exec runuser -u "$APP_USER" -- "$@"
        else
            exec "$@"
        fi
        ;;
esac
