"""Pluggable channels for one-time codes.

The SMS sender is console/log only for now — the real Nigerian provider
is wired at deployment (T18), so nothing paid can happen from dev.
Calls are read at call time through this module so tests can patch them.
"""

import logging

from django.core import mail

logger = logging.getLogger("platform")

_CODE_EMAIL_SUBJECT = "Your school platform code"


def send_code_email(user, code):
    """Email a 6-digit code (free)."""
    mail.send_mail(
        subject=_CODE_EMAIL_SUBJECT,
        message=(
            f"Hello {user.get_full_name() or user.username},\n\n"
            f"Your verification code is {code}.\n"
            "It works once and expires in 10 minutes.\n\n"
            "If you did not ask for this, ignore this message."
        ),
        from_email=None,
        recipient_list=[user.email],
        fail_silently=False,
    )


def send_code_sms(user, code):
    """Send a 6-digit code by SMS. Console implementation for now."""
    logger.info(
        "SMS to %s: your verification code is %s (single use, 10 minutes)",
        user.phone,
        code,
    )
