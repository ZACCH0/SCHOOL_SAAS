from .models import Membership
def active_memberships(user):
    """Memberships the user can act under: active membership in an active school."""
    return Membership.objects.filter(
        user=user, is_active=True, school__is_active=True
    ).select_related("school")