from pathlib import Path
import os
import ldap
from django_auth_ldap.config import LDAPSearch

BASE_DIR = Path(__file__).resolve().parent.parent

SECRET_KEY = os.getenv('SECRET_KEY', 'desarrollo-safe-key-12345')
DEBUG = os.getenv('DEBUG', 'False') == 'True'

ALLOWED_HOSTS = os.getenv('ALLOWED_HOSTS', 'localhost,127.0.0.1').split(',')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'tickets', # Nuestra Aplicación de incidencias
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

ROOT_URLCONF = 'portal.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [os.path.join(BASE_DIR, 'templates')],[cite: 1]
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

WSGI_APPLICATION = 'portal.wsgi.application'

# ---- BASE DE DATOS MIGRADA A POSTGRESQL ----
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': os.getenv('DB_NAME', 'ticketing_db'),
        'USER': os.getenv('DB_USER', 'postgres_user'),
        'PASSWORD': os.getenv('DB_PASSWORD', ''),
        'HOST': os.getenv('DB_HOST', 'db'),
        'PORT': os.getenv('DB_PORT', '5432'),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'es-es'
TIME_ZONE = 'Europe/Madrid'[cite: 1]
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = os.path.join(BASE_DIR, 'static')
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ---- CONFIGURACIÓN DE CELERY ----
CELERY_BROKER_URL = os.getenv('REDIS_URL', 'redis://redis:6379/0')[cite: 1]
CELERY_RESULT_BACKEND = os.getenv('REDIS_URL', 'redis://redis:6379/0')[cite: 1]
CELERY_TASK_ACKS_LATE = True[cite: 1]
CELERY_TIMEZONE = 'Europe/Madrid'[cite: 1]

# ---- AUTENTICACIÓN HÍBRIDA SAMBA 4 ACTIVE DIRECTORY (LDAP) ----
AUTH_LDAP_SERVER_URI = os.getenv('LDAP_SERVER', 'ldap://ad.proyecto.local')[cite: 1]
AUTH_LDAP_BIND_DN = os.getenv('LDAP_BIND_DN', '')[cite: 1]
AUTH_LDAP_BIND_PASSWORD = os.getenv('LDAP_BIND_PW', '')[cite: 1]
AUTH_LDAP_USER_SEARCH = LDAPSearch(
    os.getenv('LDAP_BASE', 'dc=proyecto,dc=local'),
    ldap.SCOPE_SUBTREE,
    "(sAMAccountName=%(user)s)"
)[cite: 1]

AUTH_LDAP_CONNECTION_OPTIONS = {
    ldap.OPT_REFERRALS: 0,
}[cite: 1]

AUTHENTICATION_BACKENDS = [
    'django_auth_ldap.backend.LDAPBackend',
    'django.contrib.auth.backends.ModelBackend',
][cite: 1]

# ---- EMAIL ----
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = os.getenv('EMAIL_HOST', 'smtp.gmail.com')
EMAIL_PORT = int(os.getenv('EMAIL_PORT', 587))
EMAIL_HOST_USER = os.getenv('EMAIL_HOST_USER', '')
EMAIL_HOST_PASSWORD = os.getenv('EMAIL_HOST_PASSWORD', '')
EMAIL_USE_TLS = True
DEFAULT_FROM_EMAIL = os.getenv('EMAIL_HOST_USER', '')
ADMIN_EMAIL = os.getenv('ADMIN_EMAIL', '')

LOGIN_REDIRECT_URL = '/tickets/'[cite: 1]
LOGOUT_REDIRECT_URL = '/login/'[cite: 1]

# ---- CONFIGURACIÓN DE ALMACENAMIENTO PARA WHITENOISE (PRODUCCIÓN) ----
STORAGES = {
    "default": {
        "BACKEND": "django.core.files.storage.FileSystemStorage",
    },
    "staticfiles": {
        "BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage",
    },
}