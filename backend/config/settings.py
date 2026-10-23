from datetime import timedelta
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent
env = environ.Env(DEBUG=(bool, False))
environ.Env.read_env(BASE_DIR / '.env')  # secrets lus depuis .env (jamais dans le code)

SECRET_KEY = env('SECRET_KEY')
DEBUG = env('DEBUG')
ALLOWED_HOSTS = env.list('ALLOWED_HOSTS', default=['localhost', '127.0.0.1'])

INSTALLED_APPS = [
    'django.contrib.admin', 'django.contrib.auth', 'django.contrib.contenttypes',
    'django.contrib.sessions', 'django.contrib.messages', 'django.contrib.staticfiles',
    'django.contrib.postgres',  # contrainte d'exclusion anti double réservation (btree_gist)
    'rest_framework', 'rest_framework_simplejwt.token_blacklist',
    'django_filters', 'corsheaders', 'drf_spectacular',
    'apps.authentication', 'apps.clients', 'apps.chambres', 'apps.reservations',
    'apps.paiements', 'apps.factures', 'apps.dashboard',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'apps.common.middleware.NoCacheMiddleware',  # en-têtes anti-cache : pas de retour arrière vers des données après déconnexion
    'corsheaders.middleware.CorsMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'config.urls'
TEMPLATES = [{
    'BACKEND': 'django.template.backends.django.DjangoTemplates',
    'DIRS': [], 'APP_DIRS': True,
    'OPTIONS': {'context_processors': [
        'django.template.context_processors.request',
        'django.contrib.auth.context_processors.auth',
        'django.contrib.messages.context_processors.messages',
    ]},
}]
WSGI_APPLICATION = 'config.wsgi.application'

# PostgreSQL (SGBDR). Les identifiants viennent du fichier .env (jamais du code).
DATABASES = {
    'default': {
        'ENGINE': 'django.db.backends.postgresql',
        'NAME': env('DB_NAME'),
        'USER': env('DB_USER'),
        'PASSWORD': env('DB_PASSWORD'),
        'HOST': env('DB_HOST', default='127.0.0.1'),
        'PORT': env('DB_PORT', default='5432'),
        'CONN_MAX_AGE': env.int('DB_CONN_MAX_AGE', default=60),
        'OPTIONS': {'connect_timeout': 10},
    }
}

AUTH_USER_MODEL = 'authentication.User'
AUTHENTICATION_BACKENDS = ['apps.authentication.backends.CaseInsensitiveEmailBackend']  # e-mail insensible à la casse
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator', 'OPTIONS': {'min_length': 10}},
    {'NAME': 'apps.common.validators.ComplexitePasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]

LANGUAGE_CODE = 'fr-fr'
TIME_ZONE = env('TIME_ZONE', default='Indian/Antananarivo')  # « aujourd'hui » = date locale de l'hôtel (UTC+3)
USE_I18N = True
USE_TZ = True
STATIC_URL = 'static/'
MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

REST_FRAMEWORK = {
    'DEFAULT_AUTHENTICATION_CLASSES': ('rest_framework_simplejwt.authentication.JWTAuthentication',),
    'DEFAULT_PERMISSION_CLASSES': ('rest_framework.permissions.IsAuthenticated',),
    'DEFAULT_FILTER_BACKENDS': (
        'django_filters.rest_framework.DjangoFilterBackend',
        'rest_framework.filters.SearchFilter',
        'rest_framework.filters.OrderingFilter',
    ),
    'DEFAULT_PAGINATION_CLASS': 'apps.common.pagination.StandardPagination',
    'PAGE_SIZE': 10,
    'DEFAULT_PARSER_CLASSES': (
        'rest_framework.parsers.JSONParser',
        'rest_framework.parsers.MultiPartParser',
        'rest_framework.parsers.FormParser',
    ),
    'DEFAULT_SCHEMA_CLASS': 'drf_spectacular.openapi.AutoSchema',
    'DEFAULT_THROTTLE_RATES': {'login': '10/min', 'register': '10/min'},  # anti force brute (par IP)
}
SIMPLE_JWT = {
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=30),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=7),
    'ROTATE_REFRESH_TOKENS': True,
    'BLACKLIST_AFTER_ROTATION': True,
}
SPECTACULAR_SETTINGS = {'TITLE': 'Hotel API', 'VERSION': '1.0.0'}

CORS_ALLOWED_ORIGINS = env.list('CORS_ALLOWED_ORIGINS', default=['http://localhost:5173'])
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'

# Règles métier / infos hôtel
CANCEL_DEADLINE_HOURS = env.int('CANCEL_DEADLINE_HOURS', default=48)
CURRENCY = env('CURRENCY', default='Ar')
# Paiement SIMULÉ (toujours accepté) : réservé au développement. En production, laisser à False tant qu'un vrai
# fournisseur (MVola, Orange Money, carte…) n'est pas branché dans apps/paiements/providers.py.
PAIEMENT_SIMULE = env.bool('PAIEMENT_SIMULE', default=DEBUG)

# Tarification (le minimum de 20 000 Ar/nuit est une constante : apps/common/constants.py + contrainte SQL).
# Tout est à 0 par défaut : une ligne de taxe ou de réduction n'apparaît que si elle est configurée dans .env.
TAXE_SEJOUR_PAR_PERSONNE_NUIT = env.int('TAXE_SEJOUR_PAR_PERSONNE_NUIT', default=0)  # Ar
TAUX_TVA = env.float('TAUX_TVA', default=0)                                          # %
REDUCTION_LONG_SEJOUR_NUITS = env.int('REDUCTION_LONG_SEJOUR_NUITS', default=7)
REDUCTION_LONG_SEJOUR_POURCENT = env.float('REDUCTION_LONG_SEJOUR_POURCENT', default=0)  # %
HOTEL_INFO = {
    'name': 'Grand Hôtel Univ',
    'address': '12 Avenue de l\'Indépendance, Antananarivo',
    'phone': '+261 34 00 000 00',
    'email': 'contact@grandhotel.example',
}

# Sécurité HTTP en production (DEBUG=False) : HTTPS, cookies sécurisés, HSTS. Derrière un reverse proxy (nginx…),
# celui-ci doit envoyer l'en-tête X-Forwarded-Proto.
if not DEBUG:
    SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
    SECURE_SSL_REDIRECT = env.bool('SECURE_SSL_REDIRECT', default=True)
    SESSION_COOKIE_SECURE = True
    CSRF_COOKIE_SECURE = True
    SECURE_HSTS_SECONDS = env.int('SECURE_HSTS_SECONDS', default=31536000)
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_CONTENT_TYPE_NOSNIFF = True
    CSRF_TRUSTED_ORIGINS = env.list('CSRF_TRUSTED_ORIGINS', default=[])
