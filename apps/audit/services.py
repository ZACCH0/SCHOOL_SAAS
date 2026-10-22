from axes.helpers import get_client_ip_address
from .models import AuditLog

def _ip(request):
    if request is None:
        return None
    try:
        return get_client_ip_address(request) or None
    except Exception:
        return None

def record(request, action, *, target=None, school=None, actor=None, **metadata):
    """Write one audit entry.

    Call it inside the same transaction as the action it describes.
    Never put passwords or tokens in `metadata`.
    """
    actor = actor or getattr(request, "user", None)
    if actor is not None and not actor.is_authenticated:
        actor = None
    school = school or getattr(request, "school", None)
    return AuditLog.objects.create(
        school=school,
        actor=actor,
        actor_label=actor.get_username() if actor else "",
        action=action,
        target_type=target._meta.label if target is not None else "",
        target_id=str(target.pk) if target is not None else "",
        target_repr=str(target)[:200] if target is not None else "",
        metadata=metadata,
        ip_address=_ip(request),
    )