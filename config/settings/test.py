from .development import *  # noqa: F401,F403

# Fast password hashing so the test suite runs quickly. Tests only, never production.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]