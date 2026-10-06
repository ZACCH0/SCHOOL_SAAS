from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.views.decorators.http import require_http_methods
from .middleware import SESSION_KEY
from .selectors import active_memberships

# Create your views here.
@login_required
@require_http_methods(["GET", "POST"])
def choose_school(request):
    memberships = active_memberships(request.user)
    error = ""

    if request.method == "POST":
        raw_id = request.POST.get("membership_id", "")
        membership = memberships.filter(pk=raw_id).first() if raw_id.isdigit() else None
        if membership:
            request.session[SESSION_KEY] = membership.pk
            return redirect("core:dashboard")
        error = "Please choose one of your own accounts."

    return render(
        request,
        "schools/choose_school.html",
        {"memberships": memberships, "error": error},
    )