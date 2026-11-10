import re

# Spaces, dashes, dots and parentheses are presentation-only when typing a phone.
_STRIP_RE = re.compile(r"[\s\-().]")
_LOCAL_11 = re.compile(r"0\d{10}")


def normalize_phone(raw):
    """Store phones in one canonical shape so logins can match them.

    Nigerian numbers: 0803 123 4567 and 234 variants come out as +234803...
    A + international number is kept as typed. Anything else is stored
    stripped, exactly as typed.
    """
    value = _STRIP_RE.sub("", (raw or "").strip())
    if not value:
        return ""
    if value.startswith("+"):
        return value
    if _LOCAL_11.fullmatch(value):
        return "+234" + value[1:]
    return value
