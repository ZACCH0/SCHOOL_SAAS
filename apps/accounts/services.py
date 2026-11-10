import hashlib
import secrets

from django.contrib.auth import password_validation
from django.core.exceptions import ValidationError
from django.db import transaction
from django.utils import timezone

from apps.audit.services import record
from apps.schools.models import Membership
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, require_role
from apps.schools.service_helpers import ensure_owned

from . import channels
from .models import OneTimeCode, SmsLog, User

CODE_TTL = timezone.timedelta(minutes=10)
MAX_CODES_PER_HOUR = 5
MAX_WRONG_ATTEMPTS = 5
CODE_REFUSAL = "That code is not right, or it has expired. Ask for a new code."
NO_CHANNEL = "This account has no email or phone number we can send a code to."
RATE_LIMITED = "Too many codes requested. Try again in about an hour."

# No 0/O, no 1/l/I: hand-typed passwords must be readable from paper.
_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"


def _hash_code(code):
    """Codes are only stored hashed. Cross-flow reuse is impossible
    because verify_code only ever looks at codes of the same purpose."""
    return hashlib.sha256(f"otc:{code}".encode("utf-8")).hexdigest()


def _case_from_user(user):
    """One-time codes are billed to the user's single active school;
    with several memberships nobody can say who pays, so it is null."""
    schools = list(
        Membership.objects.filter(user=user, school__is_active=True).values_list(
            "school_id", flat=True
        )
    )
    if len(schools) == 1:
        return schools[0]
    return None


@transaction.atomic
def issue_code(request, user, *, purpose):
    """Create and send a one-time code through email (free) or SMS.

    Refuses users with no contact channel, and enforces the rolling
    rate limit. The previous unused code is expired so only the newest
    code can ever be verified.
    """
    if user.email:
        channel = "email"
    elif user.phone:
        channel = "sms"
    else:
        raise ValidationError(NO_CHANNEL)

    hour_ago = timezone.now() - timezone.timedelta(hours=1)
    if OneTimeCode.objects.filter(user=user, purpose=purpose, created_at__gte=hour_ago).count() >= MAX_CODES_PER_HOUR:
        raise ValidationError(RATE_LIMITED)

    code = "".join(secrets.choice("0123456789") for _ in range(6))
    # Expire stale unused codes with a queryset update: they are throwaway rows.
    OneTimeCode.objects.filter(
        user=user, purpose=purpose, used_at__isnull=True
    ).update(expires_at=timezone.now())

    OneTimeCode.objects.create(
        user=user,
        purpose=purpose,
        code_hash=_hash_code(code),
        expires_at=timezone.now() + CODE_TTL,
    )

    if channel == "sms":
        SmsLog.objects.create(
            user=user, school_id=_case_from_user(user), purpose=purpose
        )
        channels.send_code_sms(user, code)
    else:
        channels.send_code_email(user, code)

    record(request, "accounts.code_issued", target=user, purpose=purpose)
    return code


def verify_code(user, purpose, code):
    """Check one code: latest of its purpose, unused, unexpired, hash match.

    Raises ValidationError with one friendly message for every refusal.
    The 5th wrong entry voids the code.
    """
    value = (code or "").strip()
    now = timezone.now()
    candidates = list(
        OneTimeCode.objects.filter(
            user=user, purpose=purpose, used_at__isnull=True
        ).order_by("-created_at")
    )
    if not candidates or candidates[0].expires_at <= now:
        raise ValidationError(CODE_REFUSAL)

    newest = candidates[0]
    if _hash_code(value) == newest.code_hash:
        newest.used_at = now
        newest.save()
        return newest

    newest.attempts = newest.attempts + 1
    if newest.attempts >= MAX_WRONG_ATTEMPTS:
        newest.expires_at = now
    newest.save()
    raise ValidationError(CODE_REFUSAL)


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
