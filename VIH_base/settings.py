import os
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent


def _load_local_env(env_path):
    """Carga pares KEY=VALUE desde .env sin requerir dependencias externas."""
    if not env_path.exists():
        return

    for raw_line in env_path.read_text(encoding='utf-8').splitlines():
        line = raw_line.strip()
        if not line or line.startswith('#') or '=' not in line:
            continue
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


_load_local_env(BASE_DIR / '.env')


def _env_bool(name, default=False):
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {'1', 'true', 'yes', 'on'}


def _env_list(name, default=None):
    value = os.environ.get(name, '')
    if not value:
        return default or []
    return [item.strip() for item in value.split(',') if item.strip()]


SECRET_KEY = os.environ.get('SECRET_KEY', 'django-insecure-dev-only-change-me')
DEBUG = _env_bool('DEBUG', True)
ALLOWED_HOSTS = _env_list('ALLOWED_HOSTS', ['localhost', '127.0.0.1'])

if DEBUG and '*' not in ALLOWED_HOSTS:
    ALLOWED_HOSTS.append('*')

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',
    'analisis_app',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'VIH_base.urls'

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

WSGI_APPLICATION = 'VIH_base.wsgi.application'

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

LANGUAGE_CODE = 'es'
TIME_ZONE = 'America/Bogota'
USE_I18N = True
USE_TZ = True

STATIC_URL = 'static/'
STATIC_ROOT = BASE_DIR / 'staticfiles'

DEFAULT_AUTO_FIELD = 'django.db.models.BigAutoField'

MEDIA_URL = '/media/'
MEDIA_ROOT = BASE_DIR / 'media'

# Configuracion Roboflow. Los secretos deben vivir en .env o variables del sistema.
ROBOFLOW_API_KEY = os.environ.get('ROBOFLOW_API_KEY', '')
ROBOFLOW_API_URL = os.environ.get('ROBOFLOW_API_URL', 'https://serverless.roboflow.com')
ROBOFLOW_VIH_MODEL_ID = os.environ.get('ROBOFLOW_VIH_MODEL_ID', 'proyecto-de-vih/1')
ROBOFLOW_SKIN_MODEL_ID = os.environ.get('ROBOFLOW_SKIN_MODEL_ID', 'proyecto-de-vih/2')
ROBOFLOW_VIH_CLASS_ID = int(os.environ.get('ROBOFLOW_VIH_CLASS_ID', '1'))
ROBOFLOW_SKIN_CLASS_ID = int(os.environ.get('ROBOFLOW_SKIN_CLASS_ID', '2'))
ROBOFLOW_DEBUG_LOGS = os.environ.get('ROBOFLOW_DEBUG_LOGS', '0')

# Umbrales anti-falsos positivos (ajustables en .env)
ROBOFLOW_MIN_VIH_PX = int(os.environ.get('ROBOFLOW_MIN_VIH_PX', '120'))
ROBOFLOW_MIN_OVERLAP_PX = int(os.environ.get('ROBOFLOW_MIN_OVERLAP_PX', '40'))
ROBOFLOW_MIN_RATIO_ALERT = float(os.environ.get('ROBOFLOW_MIN_RATIO_ALERT', '0.8'))

# Fases de severidad por porcentaje (0-100)
ROBOFLOW_FASE_NULA_MAX = float(os.environ.get('ROBOFLOW_FASE_NULA_MAX', '1.0'))
ROBOFLOW_FASE_BAJA_MAX = float(os.environ.get('ROBOFLOW_FASE_BAJA_MAX', '8.0'))
ROBOFLOW_FASE_MEDIANA_MAX = float(os.environ.get('ROBOFLOW_FASE_MEDIANA_MAX', '20.0'))

# MODELO_ML_PATH = os.path.join(BASE_DIR, 'modelo_entrenado', 'Modelo_VIH.keras')
