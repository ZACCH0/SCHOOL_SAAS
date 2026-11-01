from django.shortcuts import redirect, reverse


class ForcePasswordChangeMiddleware:
    """Send users with a forced temporary password to the change page
    until they pick a new one. Logout and static files stay reachable."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and user.must_change_password:
            exempt = (
                reverse("accounts:force_change"),
                reverse("accounts:logout"),
            )
            if request.path not in exempt and not request.path.startswith("/static/"):
                return redirect("accounts:force_change")
        return self.get_response(request)
