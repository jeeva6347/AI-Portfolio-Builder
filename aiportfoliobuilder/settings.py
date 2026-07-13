"""
Django settings for aiportfoliobuilder project.

Module 1: Authentication (Email + Google + GitHub OAuth, role-based users).
Per the SRS "Development Rules": secrets are read from environment
variables only — never hardcoded here.
"""

from pathlib import Path
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Core / security
# ---------------------------------------------------------------------------
SECRET_KEY = config("DJANGO_SECRET_KEY", default="django-insecure-change-me-in-.env")
DEBUG = config("DJANGO_DEBUG", default=True, cast=bool)
ALLOWED_HOSTS = config("DJANGO_ALLOWED_HOSTS", default="127.0.0.1,localhost", cast=Csv())

SITE_ID = 1

# ---------------------------------------------------------------------------
# Applications
# ---------------------------------------------------------------------------
INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.sites",

    # Auth / OAuth (Module 1)
    "allauth",
    "allauth.account",
    "allauth.socialaccount",
    "allauth.socialaccount.providers.google",
    "allauth.socialaccount.providers.github",

    # Local apps
    "core",
    "accounts",
    "dashboard",
    "themes",
    "portfolio",
    "analytics",
    "payments",
    "github_integration",
    "ai",
    "notifications",
    "api",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "allauth.account.middleware.AccountMiddleware",
]

ROOT_URLCONF = "aiportfoliobuilder.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "aiportfoliobuilder.wsgi.application"

# ---------------------------------------------------------------------------
# Database
# MySQL in production per SRS; falls back to sqlite for zero-setup local
# dev when DB_ENGINE is not set in .env.
# ---------------------------------------------------------------------------
if config("DB_ENGINE", default="sqlite") == "mysql":
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.mysql",
            "NAME": config("DB_NAME"),
            "USER": config("DB_USER"),
            "PASSWORD": config("DB_PASSWORD"),
            "HOST": config("DB_HOST", default="localhost"),
            "PORT": config("DB_PORT", default="3306"),
            "OPTIONS": {"charset": "utf8mb4"},
        }
    }
else:
    DATABASES = {
        "default": {
            "ENGINE": "django.db.backends.sqlite3",
            "NAME": BASE_DIR / "db.sqlite3",
        }
    }

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Custom user model (role-based: Super Admin / Admin / User)
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

AUTHENTICATION_BACKENDS = [
    "django.contrib.auth.backends.ModelBackend",
    "allauth.account.auth_backends.AuthenticationBackend",
]

# django-allauth config
ACCOUNT_LOGIN_METHODS = {"email"}
ACCOUNT_SIGNUP_FIELDS = ["email*", "username*", "password1*", "password2*"]
ACCOUNT_EMAIL_VERIFICATION = config("ACCOUNT_EMAIL_VERIFICATION", default="optional")
LOGIN_REDIRECT_URL = "accounts:dashboard_redirect"
LOGOUT_REDIRECT_URL = "accounts:login"

SOCIALACCOUNT_PROVIDERS = {
    "google": {
        "APP": {
            "client_id": config("GOOGLE_OAUTH_CLIENT_ID", default=""),
            "secret": config("GOOGLE_OAUTH_CLIENT_SECRET", default=""),
            "key": "",
        },
        "SCOPE": ["profile", "email"],
    },
    "github": {
        "APP": {
            "client_id": config("GITHUB_OAUTH_CLIENT_ID", default=""),
            "secret": config("GITHUB_OAUTH_CLIENT_SECRET", default=""),
            "key": "",
        },
        "SCOPE": ["user:email", "repo"],  # repo scope reused later by GitHub Auto Publish module
    },
}

# ---------------------------------------------------------------------------
# I18N / TZ
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static / media
# ---------------------------------------------------------------------------
STATIC_URL = "static/"
STATICFILES_DIRS = [BASE_DIR / "static"]
STATIC_ROOT = BASE_DIR / "staticfiles"

MEDIA_URL = "media/"
MEDIA_ROOT = BASE_DIR / "media"

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Email (used for password reset + email verification)
# Defaults to console backend so dev workflow needs zero setup; switch to
# smtp in .env for real delivery.
# ---------------------------------------------------------------------------
EMAIL_BACKEND = config(
    "EMAIL_BACKEND", default="django.core.mail.backends.console.EmailBackend"
)
EMAIL_HOST = config("EMAIL_HOST", default="")
EMAIL_PORT = config("EMAIL_PORT", default=587, cast=int)
EMAIL_HOST_USER = config("EMAIL_HOST_USER", default="")
EMAIL_HOST_PASSWORD = config("EMAIL_HOST_PASSWORD", default="")
EMAIL_USE_TLS = config("EMAIL_USE_TLS", default=True, cast=bool)
DEFAULT_FROM_EMAIL = config("DEFAULT_FROM_EMAIL", default="noreply@aiportfoliobuilder.com")

# ---------------------------------------------------------------------------
# Sessions (Remember Me support)
# Checked -> session lasts SESSION_COOKIE_AGE (2 weeks). Unchecked -> the
# login view sets expiry to 0, ending the session at browser close.
# ---------------------------------------------------------------------------
SESSION_COOKIE_AGE = config("SESSION_COOKIE_AGE", default=1209600, cast=int)  # 14 days
SESSION_SAVE_EVERY_REQUEST = True
