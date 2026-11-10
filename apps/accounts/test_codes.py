import hashlib

import pytest
from django.contrib.auth import get_user_model
from django.core import mail
from django.core.exceptions import ValidationError
from django.utils import timezone

from apps.accounts import channels as channel_module
from apps.accounts import services
from apps.accounts.models import OneTimeCode, SmsLog

User = get_user_model()
PURPOSE = OneTimeCode.Purpose.PASSWORD_RESET

pytestmark = pytest.mark.django_db


@pytest.fixture
def email_user():
    return User.objects.create_user(
        "emma", email="emma@example.com", password="Old-S3cure-pass!"
    )


@pytest.fixture
def phone_user():
    return User.objects.create_user(
        "halima", phone="0803 555 0101", password="Old-S3cure-pass!"
    )


@pytest.fixture
def no_channel_user():
    return User.objects.create_user("solo", password="Old-S3cure-pass!")


def _issue(request, user, purpose=PURPOSE):
    return services.issue_code(request, user, purpose=purpose)


def test_code_is_stored_hashed_with_expiry(email_user, rf):
    code = _issue(rf.post("/"), email_user)
    stored = OneTimeCode.objects.get(user=email_user)
    assert stored.purpose == PURPOSE
    assert hashlib.sha256(f"otc:{code}".encode()).hexdigest() == stored.code_hash
    assert code not in stored.code_hash
    # The raw code never lands in the database in any form.
    assert OneTimeCode.objects.filter(code_hash=code).count() == 0
    remaining = stored.expires_at - timezone.now()
    assert timezone.timedelta(minutes=9) < remaining <= timezone.timedelta(minutes=10)


def test_a_new_code_expires_the_previous_unused_one(email_user, rf):
    first = _issue(rf.post("/"), email_user)
    second = _issue(rf.post("/"), email_user)
    stored = list(OneTimeCode.objects.filter(user=email_user).order_by("created_at"))
    assert stored[0].expires_at <= timezone.now()
    # The first code no longer works; only the newest one does.
    with pytest.raises(ValidationError):
        services.verify_code(email_user, PURPOSE, first)
    assert services.verify_code(email_user, PURPOSE, second)


def test_no_channel_user_is_refused(no_channel_user, rf):
    with pytest.raises(ValidationError) as raised:
        _issue(rf.post("/"), no_channel_user)
    assert "no email or phone" in str(raised.value.messages[0])
    assert OneTimeCode.objects.count() == 0


def test_email_channel_sends_code_mail(email_user, rf):
    code = _issue(rf.post("/"), email_user)
    assert len(mail.outbox) == 1
    assert code in mail.outbox[0].body
    assert mail.outbox[0].to == ["emma@example.com"]


def test_sixth_code_inside_the_hour_is_refused(phone_user, rf):
    for _ in range(5):
        _issue(rf.post("/"), phone_user)
    with pytest.raises(ValidationError) as raised:
        _issue(rf.post("/"), phone_user)
    assert "Too many codes" in str(raised.value.messages[0])


def test_rate_limit_is_per_purpose(phone_user, rf):
    for _ in range(5):
        _issue(rf.post("/"), phone_user)
    # A different purpose has its own allowance.
    assert _issue(rf.post("/"), phone_user, purpose=OneTimeCode.Purpose.ACTIVATION)


def test_sms_channel_logs_school_and_sends_no_email(phone_user, rf, school_a, monkeypatch):
    from apps.schools.models import Membership

    Membership.objects.create(
        user=phone_user, school=school_a, role=Membership.Role.PARENT
    )
    sent = []
    monkeypatch.setattr(
        channel_module, "send_code_sms", lambda user, code: sent.append(code)
    )
    code = _issue(rf.post("/"), phone_user)
    assert sent == [code]
    assert len(mail.outbox) == 0
    log = SmsLog.objects.get(user=phone_user)
    assert log.school_id == school_a.id
    assert log.purpose == PURPOSE


def test_sms_for_user_in_two_schools_is_billed_to_none(phone_user, rf, school_a, school_b, monkeypatch):
    from apps.schools.models import Membership

    Membership.objects.create(
        user=phone_user, school=school_a, role=Membership.Role.PARENT
    )
    Membership.objects.create(
        user=phone_user, school=school_b, role=Membership.Role.PARENT
    )
    monkeypatch.setattr(channel_module, "send_code_sms", lambda user, code: None)
    _issue(rf.post("/"), phone_user)
    assert SmsLog.objects.get(user=phone_user).school_id is None


def test_wrong_code_is_refused(email_user, rf):
    _issue(rf.post("/"), email_user)
    with pytest.raises(ValidationError):
        services.verify_code(email_user, PURPOSE, "000000")


def test_used_code_cannot_be_reused(email_user, rf):
    code = _issue(rf.post("/"), email_user)
    services.verify_code(email_user, PURPOSE, code)
    with pytest.raises(ValidationError):
        services.verify_code(email_user, PURPOSE, code)


def test_expired_code_is_refused(email_user, rf):
    code = _issue(rf.post("/"), email_user)
    OneTimeCode.objects.update(expires_at=timezone.now() - timezone.timedelta(seconds=1))
    with pytest.raises(ValidationError):
        services.verify_code(email_user, PURPOSE, code)


def test_five_wrong_attempts_void_the_code(email_user, rf):
    code = _issue(rf.post("/"), email_user)
    for _ in range(5):
        with pytest.raises(ValidationError):
            services.verify_code(email_user, PURPOSE, "000000")
    # Even the correct code is dead once the guesses run out.
    with pytest.raises(ValidationError):
        services.verify_code(email_user, PURPOSE, code)
    stored = OneTimeCode.objects.get(user=email_user)
    assert stored.expires_at <= timezone.now()


def test_codes_for_different_purposes_are_independent(email_user, rf):
    reset_code = _issue(rf.post("/"), email_user, purpose=PURPOSE)
    activation_code = _issue(
        rf.post("/"), email_user, purpose=OneTimeCode.Purpose.ACTIVATION
    )
    assert reset_code != activation_code
    # A reset code must never verify as an activation code.
    with pytest.raises(ValidationError):
        services.verify_code(email_user, OneTimeCode.Purpose.ACTIVATION, reset_code)
