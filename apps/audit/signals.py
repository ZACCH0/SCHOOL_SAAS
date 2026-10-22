import logging
from django.contrib.auth.signals import user_logged_in, user_logged_out
from django.dispatch import receiver
from apps.schools.selectors import active_memberships
from .services import record
logger = logging.getLogger(__name__)


@receiver(user_logged_in)
def log_login(sender, request, user, **kwargs):
    try:
        options = list(active_memberships(user)[:2])
        school = options[0].school if len(options) == 1 else None
        record(request, "auth.login", actor=user, school=school)
    except Exception:  # an audit problem must never block a login
        logger.exception("Could not write the login audit entry")

@receiver(user_logged_out)
def log_logout(sender, request, user, **kwargs):
    try:
        if user is not None:
            record(request, "auth.logout", actor=user)
    except Exception:
        logger.exception("Could not write the logout audit entry")