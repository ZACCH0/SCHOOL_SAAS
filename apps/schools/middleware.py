from .selectors import active_memberships

SESSION_KEY = "active_membership_id"
def resolve_membership(request):
    """Return the Membership the user is acting under, or None."""
    user = request.user
    if not user.is_authenticated:
        return None

    memberships = active_memberships(user)

    chosen_id = request.session.get(SESSION_KEY)
    if chosen_id:
        membership = memberships.filter(pk=chosen_id).first()
        if membership:
            return membership
        request.session.pop(SESSION_KEY, None)

    options = list(memberships[:2])
    if len(options) == 1:
        request.session[SESSION_KEY] = options[0].pk
        return options[0]
    return None

class ActiveSchoolMiddleware:
    """Sets request.membership and request.school on every request."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.membership = resolve_membership(request)
        request.school = request.membership.school if request.membership else None
        return self.get_response(request)