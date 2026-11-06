import os

from django.core.exceptions import ImproperlyConfigured

from .base import *  # noqa: F403


if (  # noqa: F405
    SECRET_KEY == "unsafe-development-key-change-me"
    or SECRET_KEY.lower().startswith(("replace-", "generate-"))
    or len(SECRET_KEY) < 50
):
    raise ImproperlyConfigured("DJANGO_SECRET_KEY must be a unique production secret of at least 50 characters")
if DATABASES["default"]["ENGINE"] != "django.db.backends.postgresql":  # noqa: F405
    raise ImproperlyConfigured("DATABASE_URL must configure PostgreSQL in production")
if EMAIL_BACKEND in {  # noqa: F405
    "django.core.mail.backends.console.EmailBackend",
    "django.core.mail.backends.dummy.EmailBackend",
}:
    raise ImproperlyConfigured("Configure a real EMAIL_BACKEND in production")
if CACHES["default"]["BACKEND"] in {  # noqa: F405
    "django.core.cache.backends.locmem.LocMemCache",
    "django.core.cache.backends.dummy.DummyCache",
    "django.core.cache.backends.filebased.FileBasedCache",
}:
    raise ImproperlyConfigured("Configure a shared atomic cache backend in production")
DEBUG = False
DEMO_MODE = False
MIDDLEWARE.insert(1, "whitenoise.middleware.WhiteNoiseMiddleware")  # noqa: F405
ALLOWED_HOSTS = [host.strip() for host in os.getenv("ALLOWED_HOSTS", "").split(",") if host.strip()]
if not ALLOWED_HOSTS:
    raise ImproperlyConfigured("ALLOWED_HOSTS must be configured in production")
CSRF_TRUSTED_ORIGINS = [origin.strip() for origin in os.getenv("CSRF_TRUSTED_ORIGINS", "").split(",") if origin.strip()]
SECURE_SSL_REDIRECT = os.getenv("SECURE_SSL_REDIRECT", "true").lower() == "true"
if os.getenv("TRUST_X_FORWARDED_PROTO", "false").lower() == "true":
    # Enable only when a trusted reverse proxy overwrites this header and the
    # application server cannot be reached directly by untrusted clients.
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_HSTS_SECONDS = int(os.getenv("SECURE_HSTS_SECONDS", "31536000"))
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"
STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
