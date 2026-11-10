from django.contrib.auth import get_user_model

from .normalization import normalize_phone


class AmbiguousIdentifier(Exception):
    """More than one account shares this email or phone."""

    def __init__(self, field):
        self.field = field
        super().__init__(f"multiple accounts match this {field}")


def resolve_user(identifier):
    """Turn a typed username, email or phone into one real user.

    Returns the user, or None when nothing matches. Raises
    AmbiguousIdentifier when several accounts share the email/phone —
    we refuse to guess.
    """
    User = get_user_model()
    value = (identifier or "").strip()
    if not value:
        return None

    by_username = User.objects.filter(username=value)
    if by_username.count() == 1:
        return by_username.get()

    by_email = User.objects.filter(email__iexact=value)
    if by_email.count() == 1:
        return by_email.get()
    if by_email.count() > 1:
        raise AmbiguousIdentifier("email")

    phone = normalize_phone(value)
    if phone:
        by_phone = User.objects.filter(phone=phone)
        if by_phone.count() == 1:
            return by_phone.get()
        if by_phone.count() > 1:
            raise AmbiguousIdentifier("phone")

    return None
