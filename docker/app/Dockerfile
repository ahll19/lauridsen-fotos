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
RUN DJANGO_SECRET_KEY=build-time-only \
    DJANGO_STATIC_ROOT=/srv/static \
    python manage.py collectstatic --noinput --clear

# The application runs as a non-root user owning only what it needs (architecture.md §11).
# /data is bind-mounted at runtime and chowned by the entrypoint, which needs root, so the
# entrypoint drops to this user itself rather than USER doing it here.
RUN useradd --create-home --uid 1000 app \
    && mkdir -p /srv/static \
    && chown -R app:app /srv/static /app

ENTRYPOINT ["/usr/local/bin/entrypoint.sh"]
CMD ["web"]
