from .base import *  # noqa: F401,F403
from .base import env

DEBUG = False

SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=True)
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
# Keep 0 until HTTPS works end to end, then raise it (for example 31536000).
SECURE_HSTS_SECONDS = env.int("SECURE_HSTS_SECONDS", default=0)