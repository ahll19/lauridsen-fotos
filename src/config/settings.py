"""
Django settings.

Everything environment-specific is read from the environment, with a local-development
default where one is safe. Nothing operational is hardcoded — see .env.example for the
full list and what each value does.
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent


# --- Environment helpers -----------------------------------------------------


def env(name, default=None):
    value = os.environ.get(name)
    return default if value in (None, "") else value


def env_bool(name, default=False):
    return str(env(name, str(int(default)))).lower() in ("1", "true", "yes", "on")


def env_int(name, default):
    try:
        return int(env(name, default))
    except (TypeError, ValueError):
        return default


def env_list(name, default=""):
    return [item.strip() for item in str(env(name, default)).split(",") if item.strip()]


# --- Core --------------------------------------------------------------------

SECRET_KEY = env("DJANGO_SECRET_KEY", "insecure-development-key")
DEBUG = env_bool("DJANGO_DEBUG", False)

# Deploying with the shipped placeholder key would silently make every signed value on the
# site forgeable — session cookies and the client-gallery unlock cookie included. Rather than
# trusting that nobody ever copies .env.example into production, refuse to start.
_PLACEHOLDER_KEYS = {
    "insecure-development-key",
    "dev-only-insecure-key-replace-before-deploying",
    "build-time-only",
}
if not DEBUG and SECRET_KEY in _PLACEHOLDER_KEYS:
    from django.core.exceptions import ImproperlyConfigured

    raise ImproperlyConfigured(
        "DJANGO_SECRET_KEY is still the example placeholder. Generate one with:\n"
        '    python -c "import secrets; print(secrets.token_urlsafe(64))"'
    )
ALLOWED_HOSTS = env_list("DJANGO_ALLOWED_HOSTS", "localhost,127.0.0.1")
CSRF_TRUSTED_ORIGINS = env_list("DJANGO_CSRF_TRUSTED_ORIGINS")

# The admin lives at an unguessable path rather than /admin/, as a shared secret on top of
# the account password (technical_design.md §9).
ADMIN_PATH = env("DJANGO_ADMIN_PATH", "studio-admin/").strip("/") + "/"

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

INSTALLED_APPS = [
    # Must precede django.contrib.admin so it can patch the admin forms with language tabs.
    "modeltranslation",
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sitemaps",
    "django.contrib.sites",
    "easy_thumbnails",
    "ordered_model",
    "solo",
    "core",
    "portfolio",
    "timeline",
    "pages",
    "galleries",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    # Must sit between session and common middleware for the language cookie to be read.
    "django.middleware.locale.LocaleMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "django.template.context_processors.i18n",
                "core.context_processors.site_context",
                "core.context_processors.design_preview",
            ],
        },
    },
]

SITE_ID = 1


# --- Storage -----------------------------------------------------------------

# The single bind-mounted directory from architecture.md §5.
DATA_ROOT = Path(env("DATA_ROOT", BASE_DIR.parent / "data"))

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": DATA_ROOT / "db.sqlite3",
        "OPTIONS": {
            # SQLite's default rollback journal serialises readers against the writer;
            # WAL lets the site keep serving pages while a cron job writes.
            "init_command": "PRAGMA journal_mode=WAL; PRAGMA synchronous=NORMAL;",
            "transaction_mode": "IMMEDIATE",
        },
    }
}

# Originals. Deliberately NOT exposed by nginx: public pages reference derivatives only,
# and client gallery files are served through X-Accel-Redirect after an access check.
MEDIA_ROOT = DATA_ROOT / "media"
MEDIA_URL = "/media/"

# Derivatives of public images. This is the only media path nginx serves directly, and it
# lives under the disposable cache subpath so backups can skip it (architecture.md §5).
THUMBNAIL_MEDIA_ROOT = DATA_ROOT / "cache" / "thumbnails"
THUMBNAIL_MEDIA_URL = "/cache/thumbnails/"

STATIC_URL = "/static/"
STATIC_ROOT = Path(env("DJANGO_STATIC_ROOT", "/srv/static"))
STATICFILES_DIRS = [BASE_DIR / "static"]

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {
        "BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"
        if DEBUG
        else "django.contrib.staticfiles.storage.ManifestStaticFilesStorage"
    },
    # easy-thumbnails resolves its storage through this alias; without it, derivatives
    # would be written next to the originals under MEDIA_ROOT — which nginx does not
    # serve, and which backups would then have to carry.
    "easy_thumbnails": {"BACKEND": "easy_thumbnails.storage.ThumbnailFileSystemStorage"},
}
THUMBNAIL_DEFAULT_STORAGE_ALIAS = "easy_thumbnails"

# Photographs are large; hold them on disk rather than in memory while uploading.
FILE_UPLOAD_MAX_MEMORY_SIZE = 5 * 1024 * 1024
DATA_UPLOAD_MAX_MEMORY_SIZE = 10 * 1024 * 1024
DATA_UPLOAD_MAX_NUMBER_FILES = 500


# --- Images ------------------------------------------------------------------

THUMBNAIL_ALIASES = {
    "": {
        "grid": {"size": (800, 800), "crop": False, "quality": 82},
        "cover": {"size": (1200, 800), "crop": "smart", "quality": 82},
        "hero": {"size": (2000, 1200), "crop": "smart", "quality": 85},
        "lightbox": {"size": (1800, 1800), "crop": False, "quality": 85},
        "admin": {"size": (160, 160), "crop": "smart", "quality": 75},
    }
}

# Pillow re-encodes to produce each derivative, which drops EXIF — including GPS tags —
# from everything served publicly. Treated as a privacy decision, not a side effect
# (technical_design.md, "Image handling"). Orientation is applied before the data is lost.
THUMBNAIL_PRESERVE_EXTENSIONS = True
THUMBNAIL_DEFAULT_OPTIONS = {"autocrop": False}
THUMBNAIL_PROCESSORS = (
    "easy_thumbnails.processors.colorspace",
    "easy_thumbnails.processors.autocrop",
    "easy_thumbnails.processors.scale_and_crop",
    "easy_thumbnails.processors.filters",
)


# --- Internationalisation ----------------------------------------------------

LANGUAGE_CODE = env("DJANGO_LANGUAGE_CODE", "da")
TIME_ZONE = env("DJANGO_TIME_ZONE", "Europe/Copenhagen")
USE_I18N = True
USE_TZ = True

LANGUAGES = [("da", "Dansk"), ("en", "English")]
LOCALE_PATHS = [BASE_DIR / "locale"]

MODELTRANSLATION_DEFAULT_LANGUAGE = "da"
MODELTRANSLATION_LANGUAGES = ("da", "en")
# Fall back to Danish when an English translation hasn't been filled in yet, so a
# half-translated site still renders something everywhere.
MODELTRANSLATION_FALLBACK_LANGUAGES = ("da", "en")


# --- Client galleries --------------------------------------------------------

GALLERY_DEFAULT_EXPIRY_DAYS = env_int("GALLERY_DEFAULT_EXPIRY_DAYS", 90)
GALLERY_TOMBSTONE_RETENTION_DAYS = env_int("GALLERY_TOMBSTONE_RETENTION_DAYS", 30)
GALLERY_SESSION_MAX_AGE = env_int("GALLERY_SESSION_MAX_AGE", 86400)

# Hand private files off to nginx instead of streaming them through Python. Turned off
# when running manage.py runserver without a proxy in front.
USE_X_ACCEL = env_bool("USE_X_ACCEL", True)
X_ACCEL_PREFIX = "/_protected/"


# --- Email -------------------------------------------------------------------

EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", "mail-relay")
EMAIL_PORT = env_int("EMAIL_PORT", 1025)
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", False)
EMAIL_TIMEOUT = 10

DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "no-reply@localhost")
SERVER_EMAIL = env("SERVER_EMAIL", DEFAULT_FROM_EMAIL)
OWNER_EMAIL = env("OWNER_EMAIL", "owner@localhost")

# Unhandled errors are mailed through the same relay, which is the whole of the
# application-error monitoring described in architecture.md §9.
ADMINS = [("Site owner", OWNER_EMAIL)]

CONTACT_RATELIMIT = env("CONTACT_RATELIMIT", "5/h")


# --- Design preview ----------------------------------------------------------

# Lets alternative visual directions be switched on per browser while one is chosen
# (ROADMAP 0.2.0). Temporary: the winner is folded into site.css and this goes away.
# Defaults to on in development and off otherwise, so it cannot reach visitors by accident.
DESIGN_PREVIEW_ENABLED = env_bool("DESIGN_PREVIEW_ENABLED", DEBUG)
THEME_COOKIE_NAME = "design_theme"


# --- Security ----------------------------------------------------------------

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "same-origin"
SESSION_COOKIE_HTTPONLY = True
CSRF_COOKIE_HTTPONLY = False

if not DEBUG:
    # Behind nginx, which terminates TLS on the VPS.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_SSL_REDIRECT = env_bool("DJANGO_SECURE_SSL_REDIRECT", True)
    SECURE_HSTS_SECONDS = env_int("DJANGO_HSTS_SECONDS", 31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True


# --- Logging -----------------------------------------------------------------

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "simple": {"format": "[{asctime}] {levelname} {name}: {message}", "style": "{"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "simple"},
        "mail_admins": {
            "level": "ERROR",
            "class": "django.utils.log.AdminEmailHandler",
            "include_html": True,
        },
    },
    "root": {"handlers": ["console"], "level": env("DJANGO_LOG_LEVEL", "INFO")},
    "loggers": {
        "django.request": {
            "handlers": ["console", "mail_admins"],
            "level": "ERROR",
            "propagate": False,
        },
        "galleries": {"handlers": ["console"], "level": "INFO", "propagate": False},
    },
}
