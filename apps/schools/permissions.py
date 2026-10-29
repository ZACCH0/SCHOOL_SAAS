from functools import wraps
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import PermissionDenied
from .models import Membership

MANAGE_STRUCTURE_ROLES = (Membership.Role.OWNER, Membership.Role.ADMIN)

def require_role(request, roles):
    """Raise PermissionDenied unless the user is acting under one of the roles."""
    membership = getattr(request, "membership", None)
    if membership is None or membership.role not in roles:
        raise PermissionDenied
    return membership

def role_required(*roles):
    """Allow a view only for users acting under one of the given roles."""

    def decorator(view):
        @wraps(view)
        def wrapper(request, *args, **kwargs):
            if not request.user.is_authenticated:
                return redirect_to_login(request.get_full_path())
            membership = getattr(request, "membership", None)
            if membership is None or membership.role not in roles:
                raise PermissionDenied
            return view(request, *args, **kwargs)

        return wrapper

    return decorator

class RoleRequiredMixin:
    """Class-based version of role_required. Set allowed_roles on the view."""

    allowed_roles = ()

    def dispatch(self, request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        membership = getattr(request, "membership", None)
        if membership is None or membership.role not in self.allowed_roles:
            raise PermissionDenied
        return super().dispatch(request, *args, **kwargs)


def membership_required(view):
    """Any active member of a school may open this, whatever their role."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect_to_login(request.get_full_path())
        if getattr(request, "membership", None) is None:
            raise PermissionDenied
        return view(request, *args, **kwargs)

    return wrapper