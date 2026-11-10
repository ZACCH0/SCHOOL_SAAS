from django import forms
from django.contrib import messages
from django.contrib.auth import update_session_auth_hash
from django.contrib.auth.forms import PasswordResetForm, SetPasswordForm
from django.contrib.auth.views import redirect_to_login
from django.core.exceptions import ValidationError
from django.db import transaction
from django.http import Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.views.decorators.http import require_POST

from apps.audit.services import record
from apps.schools.models import Membership
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, role_required

from .forms import IdentifierForm
from .models import OneTimeCode, User
from .services import issue_code, verify_code
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


def _clear_code_session(request):
    for key in ("otp_pk", "otp_purpose", "otp_verified"):
        request.session.pop(key, None)


def password_reset_start(request):
    """Ask for one identifier, then send the right kind of reset.

    A user with an email gets the existing emailed link (free). A user
    with only a phone gets an SMS code. Unknown or ambiguous identifiers
    get the exact same generic page — nothing leaks (spec D9).
    """
    form = IdentifierForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.resolve()
        if user is not None:
            try:
                if user.email:
                    # The T7c emailed-link flow, unchanged, at no cost.
                    reset_form = PasswordResetForm(data={"email": user.email})
                    if reset_form.is_valid():
                        reset_form.save(
                            request=request,
                            use_https=request.is_secure(),
                            subject_template_name="accounts/password_reset_subject.txt",
                            email_template_name="accounts/password_reset_email.txt",
                        )
                else:
                    issue_code(
                        request,
                        user,
                        purpose=OneTimeCode.Purpose.PASSWORD_RESET,
                    )
                    request.session["otp_pk"] = user.pk
                    request.session["otp_purpose"] = str(
                        OneTimeCode.Purpose.PASSWORD_RESET
                    )
                    request.session.pop("otp_verified", None)
            except Exception:
                # Rate limits and send failures included: the reply page
                # stays identical either way (spec D9).
                pass
        return redirect("accounts:password_reset_done")
    return render(request, "accounts/password_reset_form.html", {"form": form})


def password_reset_code(request):
    """Enter the 6-digit code, then choose a new password."""
    user_pk = request.session.get("otp_pk")
    purpose = request.session.get("otp_purpose")
    if not user_pk or purpose not in OneTimeCode.Purpose.values:
        return redirect("accounts:password_reset")
    user = User.objects.filter(pk=user_pk).first()
    if user is None:
        _clear_code_session(request)
        return redirect("accounts:password_reset")

    if request.session.get("otp_verified"):
        form = SetPasswordForm(user, request.POST or None)
        if request.method == "POST" and form.is_valid():
            with transaction.atomic():
                form.user.must_change_password = False
                form.save()
                record(request, "accounts.password_changed", target=user)
            _clear_code_session(request)
            update_session_auth_hash(request, user)
            messages.success(request, "Your new password is set. You can log in now.")
            return redirect("accounts:password_reset_complete")
        return render(
            request,
            "accounts/password_reset_confirm.html",
            {"form": form, "validlink": True, "code_step": True},
        )

    error = None
    if request.method == "POST":
        try:
            verify_code(user, purpose, request.POST.get("code"))
            request.session["otp_verified"] = True
            request.session.cycle_key()
            return redirect("accounts:password_reset_code")
        except forms.ValidationError as failure:
            error = "; ".join(failure.messages)

    return render(
        request,
        "accounts/password_reset_code.html",
        {"error": error},
    )


def activate(request, uidb64):
    """First login for users created with an unusable password.

    The office hands over this link privately, like a reset token.
    The new user then proves ownership of their email/phone with a
    one-time code before choosing a password.
    """
    try:
        user_pk = int(urlsafe_base64_decode(uidb64))
    except (ValueError, TypeError):
        user_pk = None
    user = User.objects.filter(pk=user_pk).first() if user_pk else None
    if user is None or user.has_usable_password():
        return redirect_to_login(request.get_full_path())

    try:
        issue_code(request, user, purpose=OneTimeCode.Purpose.ACTIVATION)
    except ValidationError:
        # No contact channel to send a code to: the office should use
        # the temporary-password reset (T7d) for this account instead.
        return redirect_to_login(request.get_full_path())

    _clear_code_session(request)
    request.session["otp_pk"] = user.pk
    request.session["otp_purpose"] = str(OneTimeCode.Purpose.ACTIVATION)
    return redirect("accounts:password_reset_code")
