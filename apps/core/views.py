from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from apps.schools.selectors import active_memberships


def home(request):
    return render(request, "core/home.html")

@login_required
def dashboard(request):
    count = active_memberships(request.user).count()

    if request.membership is None:
        if count > 1:
            return redirect("schools:choose")
        if request.user.is_superuser:
            return redirect("admin:index")
        return render(request, "core/no_access.html", status=403)

    return render(request, "core/dashboard.html", {"has_multiple": count > 1})