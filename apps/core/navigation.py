from django.urls import reverse

# (label, url name, allowed roles). None means every role.
# Add one line here when a module's page exists.
NAV_ITEMS = [
    ("Dashboard", "core:dashboard", None),
]


def nav_for(request, membership):
    current = request.resolver_match.view_name if request.resolver_match else ""
    items = []
    for label, url_name, roles in NAV_ITEMS:
        if roles is not None and membership.role not in roles:
            continue
        items.append(
            {"label": label, "url": reverse(url_name), "active": url_name == current}
        )
    return items