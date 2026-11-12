# One image, two roles: the web application and its scheduled jobs. Sharing the image is
# what keeps "what runs the app" and "what runs its jobs" from drifting apart
# (architecture.md §4).

FROM python:3.12-slim-bookworm

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    DJANGO_SETTINGS_MODULE=config.settings

# libjpeg/zlib are Pillow's runtime dependencies; cron runs the scheduled jobs; gettext
# compiles the translation catalogues.
RUN apt-get update && apt-get install -y --no-install-recommends \
        cron \
        gettext \
        libjpeg62-turbo \
        zlib1g \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY pyproject.toml ./
COPY src/ ./src/
COPY docker/app/entrypoint.sh docker/app/crontab.template /usr/local/bin/
RUN chmod +x /usr/local/bin/entrypoint.sh

WORKDIR /app/src

# Collect static assets at build time, as technical_design.md specifies. The entrypoint
# repeats this into the shared volume at startup so a rebuilt image is picked up without
# having to recreate the volume.
#
# Django refuses to start without a SECRET_KEY, and collectstatic is a full Django startup,
# so the build needs *a* value. It is generated here and thrown away rather than being a
# fixed literal: a memorable placeholder is the kind of thing that gets copied into a real
# .env. Nothing signed at build time is ever verified at runtime, so this value has no
# security meaning — and settings.py refuses to boot in production with a placeholder key,
# which is the failure this actually guards against.
RUN DJANGO_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
    DJANGO_STATIC_ROOT=/srv/static \
    python manage.py collectstatic --noinput --clear

# The application runs as a non-root user (architecture.md §11). The entrypoint starts as
# root only long enough to make the bind-mounted /data writable, then replaces itself with
# the application under this uid via setpriv — so a running container has no root process at
# all. The uid is fixed at build time so the host can pre-own /data with a matching owner,
# and is a build argument so it can be one no account on the host already holds (APP_UID).
ARG APP_UID=1000
RUN useradd --create-home --uid "$APP_UID" app \
    && mkdir -p /srv/static \
    && chown -R app:app /srv/static /app

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["web"]
