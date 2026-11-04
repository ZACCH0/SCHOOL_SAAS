from .development import *  # noqa: F401,F403
import tempfile
from pathlib import Path

# Fast password hashing so the test suite runs quickly. Tests only, never production.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]

MEDIA_ROOT = Path(tempfile.gettempdir()) / "school-saas-test-media"