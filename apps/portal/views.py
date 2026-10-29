from django.shortcuts import render

from apps.schools.models import Membership
from apps.schools.permissions import role_required

from .selectors import children_for

StatusChip = {
    "active": ("ok", "Active"),
    "graduated": ("neutral", "Graduated"),
    "withdrawn": ("bad", "Withdrawn"),
    "suspended": ("warn", "Suspended"),
    "transferred": ("info", "Transferred"),
}


@role_required(Membership.Role.PARENT)
def children(request):
    kids = children_for(request.membership)
    for kid in kids:
        kid.status_kind, kid.status_label = StatusChip.get(
            kid.status, ("neutral", kid.get_status_display())
        )
    return render(request, "portal/children.html", {"children": kids})
