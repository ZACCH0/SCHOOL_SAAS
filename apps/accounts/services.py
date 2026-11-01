import secrets

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import record
from apps.schools.models import Membership
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, require_role
from apps.schools.service_helpers import ensure_owned

from .models import User

# No 0/O, no 1/l/I: hand-typed passwords must be readable from paper.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"


def generate_temp_password(length=12):
    """A random password that passes the project's password validators."""
    rng = secrets.SystemRandom()
    for _ in range(20):
        candidate = "".join(rng.choice(_ALPHABET) for _ in range(length))
        try:
            password_validation.validate_password(candidate)
        except ValidationError:
            continue
        return candidate
    return candidate


@transaction.atomic
def reset_password(request, membership):
    """Give a school member a new temporary password they must change at next login.

    Only owner and admin may do this. The password itself is never audited;
    it is returned once for the acting admin to hand over privately.
    """
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, membership)

    temporary = generate_temp_password()
    user = User.objects.get(pk=membership.user_id)
    user.set_password(temporary)
    # set_password does not save; both fields go in one update.
    user.must_change_password = True
    user.save()

    record(
        request, "accounts.password_reset", target=user,
        membership_role=membership.get_role_display(),
    )
    return temporary
