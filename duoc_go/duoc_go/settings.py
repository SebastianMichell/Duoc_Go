# duoc_go/duoc_go/settings.py

import os
from pathlib import Path
from dotenv import load_dotenv
import dj_database_url

# --- 1. Carga de Variables y Rutas Base ---
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent


# --- 2. Configuración de Seguridad y Despliegue ---
# Leemos las claves secretas desde las variables de entorno (.env o Render)
SECRET_KEY = os.environ.get('SECRET_KEY')
DEBUG = os.environ.get('DEBUG', 'False').lower() == 'true'

# Configuración de HOSTS (la que arregla tu Error 500)
ALLOWED_HOSTS = ['127.0.0.1']
RENDER_EXTERNAL_HOSTNAME = os.environ.get('RENDER_EXTERNAL_HOSTNAME')
if RENDER_EXTERNAL_HOSTNAME:
    ALLOWED_HOSTS.append(RENDER_EXTERNAL_HOSTNAME)


# --- 3. Aplicaciones ---
INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'whitenoise.runserver_nostatic',
    'django.contrib.staticfiles',
    'cloudinary_storage',
    'cloudinary',
    'core',
    'products_a',
    'products_b',
    "tailwind",
    'rest_framework',
]

# --- 4. Middleware ---
MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'whitenoise.middleware.WhiteNoiseMiddleware', # <--- AÑADIDO (para Whitenoise)
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

# --- 5. Configuración de URLs y Plantillas ---
ROOT_URLCONF = 'duoc_go.urls'
WSGI_APPLICATION = 'duoc_go.wsgi.application'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [BASE_DIR / "templates"],
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

# --- 6. Bases de Datos (Configuración de Producción) ---
DATABASES = {
    'default': dj_database_url.config(
        default=os.environ.get('DATABASE_URL'), # <-- De Render
        conn_max_age=600,
        ssl_require=True
    ),
    'secondary': dj_database_url.config(
        default=os.environ.get('SECONDARY_DATABASE_URL'), # <-- De Neon
        conn_max_age=600,
        ssl_require=True
    )
}

# Router para las dos bases de datos
DATABASE_ROUTERS = ["duoc_go.dbrouters.ProductsRouter"]


# --- 7. Autenticación ---
AUTH_PASSWORD_VALIDATORS = [
    {'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator'},
    {'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator'},
    {'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator'},
    {'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator'},
]
AUTH_USER_MODEL = 'core.CustomUser'
AUTHENTICATION_BACKENDS = [
    "core.backends.EmailOrRUTBackend",
    "django.contrib.auth.backends.ModelBackend",
]

# --- 8. Internacionalización ---
LANGUAGE_CODE = 'es-cl' # Cambiado a español de Chile
TIME_ZONE = 'America/Santiago'
USE_I18N = True
USE_TZ = True


# --- 9. Archivos Estáticos (CSS, JS) y Media (Uploads) ---
STATIC_URL = '/static/'

# Configuración de WHITENOISE (para producción)
STATIC_ROOT = BASE_DIR / 'staticfiles'
STATICFILES_STORAGE = 'whitenoise.storage.CompressedManifestStaticFilesStorage'


# --- 10. Configuración de Email (SendGrid) ---
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.sendgrid.net' 
EMAIL_PORT = 587             
EMAIL_USE_TLS = True        
EMAIL_USE_SSL = False         
EMAIL_HOST_USER = 'apikey'
EMAIL_HOST_PASSWORD = os.environ.get('EMAIL_HOST_PASSWORD')
DEFAULT_FROM_EMAIL = 'jexfryxd@gmail.com'
EMAIL_TIMEOUT = 30


# --- 11. Otros ---
DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'
TAILWIND_APP_NAME = "theme"

# --- 12. Configuración de Cloudinary (para Archivos MEDIA) ---

DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'
DEFAULT_FILE_STORAGE = 'cloudinary_storage.storage.MediaCloudinaryStorage'