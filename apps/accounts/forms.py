from django import forms
from django.contrib.auth import authenticate
from django.contrib.auth.forms import AuthenticationForm
from django.core.exceptions import ValidationError as FormValidationError

from .identification import AmbiguousIdentifier, resolve_user


class IdentifierAuthenticationForm(AuthenticationForm):
    """Log in with username, email or phone — then the password.

    The identifier is resolved to a real user first, then the resolved
    username is authenticated so django-axes locks (username + IP)
    exactly like before.
    """

    username = forms.CharField(label="Username, email or phone", max_length=254)

    def clean(self):
        username = self.cleaned_data.get("username")
        password = self.cleaned_data.get("password")
        if not username or not password:
            # Field-level errors handle empty values.
            return self.cleaned_data

        try:
            account = resolve_user(username)
        except AmbiguousIdentifier as failure:
            raise FormValidationError(
                "More than one account matches that "
                f"{failure.field}. Please sign in with your username.",
                code="ambiguous_identifier",
            )

        if account is None:
            raise self.get_invalid_login_error()

        self.user_cache = authenticate(
            self.request, username=account.username, password=password
        )
        if self.user_cache is None:
            raise self.get_invalid_login_error()
        self.confirm_login_allowed(self.user_cache)
        return self.cleaned_data

    def get_invalid_login_error(self):
        # Same wording as the stock form: the template shows
        # "Wrong username or password." against every identifier type,
        # so probing teaches nothing about which accounts exist.
        return FormValidationError(
            self.error_messages["invalid_login"],
            code="invalid_login",
            params={"username": self.username_field.verbose_name},
        )


class IdentifierForm(forms.Form):
    """Step one of password reset: one identifier box, like the login page."""

    identifier = forms.CharField(label="Username, email or phone", max_length=254)

    def resolve(self):
        """The matched user, or None — every refusal looks the same."""
        try:
            return resolve_user(self.cleaned_data.get("identifier") or "")
        except AmbiguousIdentifier:
            # Deliberately hidden here: the reset replies one generic page.
            return None
