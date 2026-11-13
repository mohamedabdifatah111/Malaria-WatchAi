import glob
import os
from pathlib import Path

import environ

BASE_DIR = Path(__file__).resolve().parent.parent.parent  # backend/
PROJECT_ROOT = BASE_DIR.parent  # repository root, where .env lives

env = environ.Env()
environ.Env.read_env(PROJECT_ROOT / ".env")

# GDAL/GEOS on Windows via OSGeo4W. On Linux/macOS leave OSGEO4W_ROOT empty and
# install GDAL/GEOS system-wide.
OSGEO4W_ROOT = env("OSGEO4W_ROOT", default="")
if OSGEO4W_ROOT and os.name == "nt":
    _root = os.path.normpath(OSGEO4W_ROOT)
    _bin = os.path.join(_root, "bin")
    _dll_handle = os.add_dll_directory(_bin)
    os.environ["PATH"] = _bin + os.pathsep + os.environ.get("PATH", "")
    os.environ["GDAL_DATA"] = os.path.join(_root, "apps", "gdal", "share", "gdal")
    os.environ["PROJ_LIB"] = os.path.join(_root, "share", "proj")
    os.environ["PROJ_DATA"] = os.environ["PROJ_LIB"]
    GEOS_LIBRARY_PATH = os.path.join(_bin, "geos_c.dll")
    _gdal_libs = sorted(glob.glob(os.path.join(_bin, "gdal[0-9]*.dll")))
    if _gdal_libs:
        GDAL_LIBRARY_PATH = _gdal_libs[0]

# Required: the app refuses to start without a secret key.
SECRET_KEY = env("DJANGO_SECRET_KEY")
DEBUG = False
ALLOWED_HOSTS = env.list("DJANGO_ALLOWED_HOSTS", default=[])

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.gis",
    # Third party
    "rest_framework",
    "rest_framework.authtoken",
    "corsheaders",
    "django_filters",
    "drf_spectacular",
    # Local
    "apps.core",
    "apps.accounts",
    "apps.evidence",
    "apps.geography",
    "apps.prevalence",
    "apps.population",
    "apps.species",
    "apps.drug_efficacy",
    "apps.resistance",
    "apps.assistant",
    "apps.environment",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "corsheaders.middleware.CorsMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
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

DATABASES = {
    "default": {
        "ENGINE": "django.contrib.gis.db.backends.postgis",
        "NAME": env("DB_NAME"),
        "USER": env("DB_USER"),
        "PASSWORD": env("DB_PASSWORD"),
        "HOST": env("DB_HOST", default="localhost"),
        "PORT": env("DB_PORT", default="5432"),
    }
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

X_FRAME_OPTIONS = "DENY"
SECURE_CONTENT_TYPE_NOSNIFF = True

# CORS: approved frontend origins only.
CORS_ALLOW_ALL_ORIGINS = False
CORS_ALLOWED_ORIGINS = env.list("CORS_ALLOWED_ORIGINS", default=[])

# AI assistant: Google Gemini writes the brief summary from retrieved findings.
# Leave GEMINI_API_KEY empty to use the deterministic template summary only.
GEMINI_API_KEY = env("GEMINI_API_KEY", default="")
GEMINI_MODEL = env("GEMINI_MODEL", default="gemini-3.8-flash")
GEMINI_TIMEOUT_S = env.float("GEMINI_TIMEOUT_S", default=20.0)
ASSISTANT_LLM_ENABLED = env.bool("ASSISTANT_LLM_ENABLED", default=True)

REST_FRAMEWORK = {
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework.authentication.TokenAuthentication",
        "rest_framework.authentication.SessionAuthentication",
    ],
    # Reads are public; any write needs an authenticated user.
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticatedOrReadOnly",
    ],
    "DEFAULT_RENDERER_CLASSES": ["apps.core.renderers.EnvelopeJSONRenderer"],
    "DEFAULT_PARSER_CLASSES": ["rest_framework.parsers.JSONParser"],
    "DEFAULT_PAGINATION_CLASS": "apps.core.pagination.StandardPagination",
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
    ],
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
    "DEFAULT_THROTTLE_CLASSES": [
        "rest_framework.throttling.AnonRateThrottle",
        "rest_framework.throttling.UserRateThrottle",
    ],
    "DEFAULT_THROTTLE_RATES": {
        "anon": "60/min",
        "user": "120/min",
        "login": "10/min",
        "brief": "20/min",
        "review": "60/min",
        "weather": "30/min",
        "map": "30/min",
    },
    "EXCEPTION_HANDLER": "apps.core.exceptions.api_exception_handler",
}

SPECTACULAR_SETTINGS = {
    "TITLE": "Malaria WatchAI API",
    "DESCRIPTION": "Malaria surveillance and decision-support API for Kenya, Tanzania and Ethiopia.",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "structured": {"format": "%(asctime)s %(levelname)s %(name)s %(message)s"},
    },
    "handlers": {
        "console": {"class": "logging.StreamHandler", "formatter": "structured"},
    },
    "root": {"handlers": ["console"], "level": env("LOG_LEVEL", default="INFO")},
}