from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.db.models import Q
from django.db.models.functions import Lower

from .normalization import normalize_phone


class User(AbstractUser):
    """Platform user. Username login; email and phone are optional."""

    phone = models.CharField(max_length=20, blank=True)
    must_change_password = models.BooleanField(default=False, db_index=True)

    class Meta(AbstractUser.Meta):
        constraints = [
            models.UniqueConstraint(
                Lower("email"),
                condition=~Q(email=""),
                name="accounts_user_unique_email_when_set",
            ),
            models.UniqueConstraint(
                fields=["phone"],
                condition=~Q(phone=""),
                name="accounts_user_unique_phone_when_set",
            ),
        ]

    def __str__(self):
        return self.get_full_name() or self.username

    def save(self, *args, **kwargs):
        # Phones are stored in one canonical shape so that logging in
        # with a differently formatted phone still matches the account.
        if self.phone:
            self.phone = normalize_phone(self.phone)
        super().save(*args, **kwargs)


class OneTimeCode(models.Model):
    """A single-use 6-digit code sent by email or SMS.

    The raw code is never stored, only its hash. Used for password reset
    and account activation; never as a login method.
    """

    class Purpose(models.TextChoices):
        PASSWORD_RESET = "password_reset", "Password reset"
        ACTIVATION = "activation", "Account activation"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="one_time_codes",
    )
    purpose = models.CharField(max_length=20, choices=Purpose.choices)
    code_hash = models.CharField(max_length=64)
    expires_at = models.DateTimeField()
    used_at = models.DateTimeField(null=True, blank=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(
                fields=["user", "purpose", "created_at"],
                name="otc_user_purpose_created",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} {self.purpose} ({self.created_at:%Y-%m-%d %H:%M})"


class SmsLog(models.Model):
    """One row per SMS the platform sent, so credit can be billed per school.

    school is null when the user has no single unambiguous school
    membership — those messages are platform-paid.
    """

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="sms_logs",
    )
    school = models.ForeignKey(
        "schools.School", null=True, blank=True, on_delete=models.PROTECT
    )
    purpose = models.CharField(max_length=20, choices=OneTimeCode.Purpose.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=["school", "created_at"], name="smslog_school_created"),
        ]

    def __str__(self):
        return f"{self.user_id} {self.purpose} ({self.created_at:%Y-%m-%d %H:%M})"
