"""
Django settings for My Wallet - Personal Finance Manager

Sensitive values are loaded from environment variables / .env file.
Copy .env.example → .env and fill in your credentials before running.
"""

from pathlib import Path
import os
from decouple import config, Csv

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Security ──────────────────────────────────────────────────────────────────
SECRET_KEY = config(
    'SECRET_KEY',
    default='django-insecure-fintrack-change-this-in-production-xyz123abc456'
)
DEBUG = config('DEBUG', default=True, cast=bool)
ALLOWED_HOSTS = config('ALLOWED_HOSTS', default='*', cast=Csv())

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'crispy_forms',
    'crispy_tailwind',
    'django_apscheduler',
    'core',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'fintrack.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / 'templates'],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'fintrack.wsgi.application'

DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.sqlite3',
        'NAME': BASE_DIR / 'db.sqlite3',
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'en-us'
TIME_ZONE = 'UTC'
USE_I18N = True
USE_TZ = True

STATIC_URL = '/static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'

# ── Media Files (User Uploads) ────────────────────────────────────────────────
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

LOGIN_URL = '/login/'
LOGIN_REDIRECT_URL = '/dashboard/'
LOGOUT_REDIRECT_URL = '/login/'

CRISPY_ALLOWED_TEMPLATE_PACKS = "tailwind"
CRISPY_TEMPLATE_PACK = "tailwind"

MESSAGE_STORAGE = 'django.contrib.messages.storage.session.SessionStorage'

# ── Email (SMTP) ──────────────────────────────────────────────────────────────
# Set EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend in .env
# while developing without a real SMTP server.  For production use SMTP.
EMAIL_BACKEND = config(
    'EMAIL_BACKEND',
    default='django.core.mail.backends.smtp.EmailBackend',
)
EMAIL_HOST          = config('EMAIL_HOST',          default='smtp.gmail.com')
EMAIL_PORT          = config('EMAIL_PORT',          default=587, cast=int)
EMAIL_USE_TLS       = config('EMAIL_USE_TLS',       default=True, cast=bool)
EMAIL_USE_SSL       = config('EMAIL_USE_SSL',       default=False, cast=bool)
EMAIL_HOST_USER     = config('EMAIL_HOST_USER',     default='')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD', default='')
DEFAULT_FROM_EMAIL  = config(
    'DEFAULT_FROM_EMAIL',
    default=f'My Wallet <{EMAIL_HOST_USER}>',
)
EMAIL_TIMEOUT       = config('EMAIL_TIMEOUT',       default=10, cast=int)

# ── OTP settings ─────────────────────────────────────────────────────────────
OTP_EXPIRY_MINUTES  = config('OTP_EXPIRY_MINUTES',  default=10, cast=int)
OTP_MAX_ATTEMPTS    = config('OTP_MAX_ATTEMPTS',    default=5,  cast=int)
OTP_MAX_RESENDS     = config('OTP_MAX_RESENDS',     default=3,  cast=int)
