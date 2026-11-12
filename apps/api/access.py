from django.core.exceptions import PermissionDenied

from apps.schools.selectors import active_memberships


def api_membership(request):
    """The membership an API request acts under, or None.

    Browser requests already carry request.membership from
    ActiveSchoolMiddleware (resolved through the session). Token
    requests have no session, so the membership comes from the user
    directly: exactly one active membership, otherwise the request is
    refused — a device has no school chooser, so multi-school users
    pick their school on the website first.
    """
    membership = getattr(request, "membership", None)
    if membership is not None:
        return membership
    options = list(active_memberships(request.user)[:2])
    if len(options) == 1:
        return options[0]
    return None


def require_api_role(request, roles):
    """403 unless the request acts under one of the allowed roles."""
    membership = api_membership(request)
    if membership is None or membership.role not in roles:
        raise PermissionDenied
    return membership
