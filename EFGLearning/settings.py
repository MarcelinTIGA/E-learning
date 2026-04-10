"""
EFG E-Learning — Settings (fichier chargé par manage.py)

NOTE ARCHITECTURE :
Ce fichier est chargé quand on lance :
    python EFGLearning/manage.py ...
car manage.py ajoute /home/.../afroLearning au sys.path,
ce qui fait que Python trouve le paquet EFGLearning/ ici en premier.

Le contenu est identique à EFGLearning/EFGLearning/settings.py,
sauf BASE_DIR qui est ajusté (ce fichier est un niveau plus haut).
"""

from pathlib import Path
from datetime import timedelta
import environ

# BASE_DIR pointe vers le dossier EFGLearning/ (là où se trouve le .env)
# Path(__file__).resolve() = /...afroLearning/EFGLearning/settings.py
# .parent = /...afroLearning/EFGLearning/
BASE_DIR = Path(__file__).resolve().parent

env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / '.env')

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

AUTH_USER_MODEL = 'ElearningApp.User'

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    # WhiteNoise doit être avant staticfiles pour prendre la main en développement
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    # Packages tiers
    'rest_framework',
    'rest_framework_simplejwt',
    'corsheaders',
    # Applications EFG
    'ElearningApp',
]

MIDDLEWARE = [
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.security.SecurityMiddleware',
    # WhiteNoise doit être juste après SecurityMiddleware (avant tout le reste)
    'whitenoise.middleware.WhiteNoiseMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'EFGLearning.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'EFGLearning.wsgi.application'

DATABASES = {
    'default': env.db('DATABASE_URL', default=f'sqlite:///{BASE_DIR}/db.sqlite3')
}

AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = 'Africa/Abidjan'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
# STATIC_ROOT : destination de `python manage.py collectstatic`
# WhiteNoise sert les fichiers depuis ce répertoire en production
STATIC_ROOT = BASE_DIR / 'staticfiles'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# WhiteNoise — compression Brotli/gzip + hash dans les noms de fichiers (cache navigateur)
STORAGES = {
    'default': {
        'BACKEND': 'django.core.files.storage.FileSystemStorage',
    },
    'staticfiles': {
        'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage',
    },
}

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

# ── Sécurité HTTPS (uniquement en production, quand DEBUG=False) ───────────────
if not DEBUG:
    # Redirige HTTP → HTTPS automatiquement
    SECURE_SSL_REDIRECT = True
    # HSTS : le navigateur refuse d'accéder au site en HTTP pendant 1 an
    SECURE_HSTS_SECONDS = 31536000
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = True
    # Les cookies ne transitent que via HTTPS
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    # Nécessaire derrière un reverse proxy (Nginx, Caddy, Render, Railway...)
    # Le proxy termine le SSL et transmet en HTTP au serveur Django
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')

# Origines autorisées pour les soumissions CSRF (admin Django, formulaires)
# Ex : CSRF_TRUSTED_ORIGINS=https://efg-learning.com,https://www.efg-learning.com
CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])

# ── Django REST Framework ──────────────────────────────────────────────────
REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'rest_framework_simplejwt.authentication.JWTAuthentication',
    ),
    'DEFAULT_PERMISSION_CLASSES': (
        'rest_framework.permissions.IsAuthenticated',
    ),
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'PAGE_SIZE': 20,
    # En production : JSON uniquement (désactive l'interface HTML navigable du DRF)
    # En développement : l'interface HTML reste disponible pour tester dans le navigateur
    'DEFAULT_RENDERER_CLASSES': (
        'rest_framework.renderers.JSONRenderer',
        'rest_framework.renderers.BrowsableAPIRenderer',
    ) if DEBUG else (
        'rest_framework.renderers.JSONRenderer',
    ),
}

# ── JWT ────────────────────────────────────────────────────────────────────
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(hours=2),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=30),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': False,
    'AUTH_HEADER_TYPES': ('Bearer',),
}

# ── CORS (pour Flutter) ────────────────────────────────────────────────────
CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=[])
CORS_ALLOW_ALL_ORIGINS = DEBUG
