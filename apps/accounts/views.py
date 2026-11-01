from django import forms
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import SetPasswordForm
from django.contrib.auth.views import redirect_to_login
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.audit.services import record
from apps.schools.models import Membership
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, role_required

from .services import reset_password


def _dashboard(request):
    return redirect("core:dashboard")


def force_change(request):
    """The page a user with a temporary password is kept on."""
    user = request.user
    if not user.is_authenticated:
        return redirect_to_login(request.get_full_path())
    if not user.must_change_password:
        return _dashboard(request)

    form = SetPasswordForm(user, request.POST or None)
    if request.method == "POST" and form.is_valid():
        # form.save() writes the new hash and every other field together.
        form.user.must_change_password = False
        with transaction.atomic():
            form.save()
            record(request, "accounts.password_changed", target=user)
        update_session_auth_hash(request, user)
        messages.success(request, "Your new password is set. Welcome back.")
        return _dashboard(request)
    return render(request, "accounts/force_change.html", {"form": form})


@role_required(*MANAGE_STRUCTURE_ROLES)
@require_POST
def member_password_reset(request, pk):
    """An owner or admin gives a school member a temporary password."""
    membership = (
        Membership.objects.select_related("user")
        .filter(pk=pk, school=request.school)
        .first()
    )
    if membership is None:
        raise Http404

    temporary = reset_password(request, membership)
    user = membership.user
    messages.success(
        request,
        f"Temporary password for {user.get_full_name() or user.username} ({user.username}): "
        f"{temporary} — share it privately; they must change it at next login.",
    )
    safe_next = request.POST.get("next") or ""
    if not url_has_allowed_host_and_scheme(safe_next, request.get_host()):
        return redirect("students:parent_list")
    return redirect(safe_next)
