from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from apps.academics.selectors import current_or_last_period, current_session
from apps.schools.models import Membership
from apps.schools.selectors import active_memberships

from .selectors import (
    MANAGER_ROLES,
    bursar_dashboard,
    manager_dashboard,
    parent_dashboard,
    teacher_dashboard,
)


def home(request):
    return render(request, "core/home.html")


def _dashboard_for(role, school, membership, period):
    """Read-only dashboard data for this member's role. Every participating
    app is school-scoped, so nothing from another school can ever leak in."""
    if role == Membership.Role.BURSAR:
        return {"role_key": "bursar", **bursar_dashboard(school, period)}
    if role == Membership.Role.TEACHER:
        return {"role_key": "teacher", **teacher_dashboard(school, membership, period)}
    if role == Membership.Role.PARENT:
        return {"role_key": "parent", **parent_dashboard(school, membership, period)}
    if role in MANAGER_ROLES:
        return {"role_key": "manager", **manager_dashboard(school, period)}
    # Student role (and anything not built yet): plain welcome only.
    return {"role_key": ""}


@login_required
def dashboard(request):
    count = active_memberships(request.user).count()

    if request.membership is None:
        if count > 1:
            return redirect("schools:choose")
        if request.user.is_superuser:
            return redirect("admin:index")
        return render(request, "core/no_access.html", status=403)

    session = current_session(request.school)
    period = current_or_last_period(session) if session else None
    context = {
        "has_multiple": count > 1,
        "session": session,
        "period": period,
        **_dashboard_for(
            request.membership.role, request.school, request.membership, period,
        ),
    }
    return render(request, "core/dashboard.html", context)
