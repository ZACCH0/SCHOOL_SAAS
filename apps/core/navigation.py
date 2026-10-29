from django.urls import reverse

from apps.schools.models import Membership

Role = Membership.Role
MANAGERS = [Role.OWNER, Role.ADMIN]

# A teacher marks the register, so attendance stays visible to teachers too.
ATTENDANCE_ROLES = [Role.OWNER, Role.ADMIN, Role.TEACHER]

# Teachers enter and submit scores, so results are visible to them too.
RESULTS_ROLES = [Role.OWNER, Role.ADMIN, Role.TEACHER]

# Finance is for the school office only (the bursar handles money).
FEES_ROLES = [Role.OWNER, Role.ADMIN, Role.BURSAR]

# Parents only see their own children through this portal entry.
PORTAL_ROLES = [Role.PARENT]

# (label, url name, allowed roles). None means every role.
# Add one line here when a module's page exists.
NAV_ITEMS = [
    ("Dashboard", "core:dashboard", None),
    ("Notifications", "notifications:list", None),
    ("Attendance", "attendance:home", ATTENDANCE_ROLES),
    ("Results", "results:home", RESULTS_ROLES),
    ("Students", "students:list", MANAGERS),
    ("Classes", "classes:list", MANAGERS),
    ("Subjects", "subjects:list", MANAGERS),
    ("Fees", "fees:home", FEES_ROLES),
    ("My children", "portal:children", PORTAL_ROLES),
]


def _is_active(url_name, current):
    if url_name == current:
        return True
    namespace = url_name.split(":")[0]
    return namespace != "core" and current.split(":")[0] == namespace


def nav_for(request, membership):
    current = request.resolver_match.view_name if request.resolver_match else ""
    items = []
    for label, url_name, roles in NAV_ITEMS:
        if roles is not None and membership.role not in roles:
            continue
        items.append(
            {"label": label, "url": reverse(url_name), "active": _is_active(url_name, current)}
        )
    return items
