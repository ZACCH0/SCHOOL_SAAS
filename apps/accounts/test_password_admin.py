from django.contrib.auth import get_user_model
from django.urls import reverse

import pytest

from apps.audit.models import AuditLog
from apps.schools.models import Membership

User = get_user_model()

pytestmark = pytest.mark.django_db


@pytest.fixture
def parent_membership(school_a):
    user = User.objects.create_user(
        "parent1", password="Parent@1", first_name="Parent", last_name="One",
    )
    return Membership.objects.create(
        user=user, school=school_a, role=Membership.Role.PARENT,
    )


def _manager(client, school, role=Membership.Role.OWNER):
    user = User.objects.create_user(
        f"manager-{role}-{User.objects.count()}", password="S3cure-pass!",
    )
    Membership.objects.create(user=user, school=school, role=role)
    client.force_login(user)
    return user


def _reset(client, membership, follow=False):
    return client.post(
        reverse("accounts:member_password_reset", args=[membership.pk]),
        {"next": ""},
        follow=follow,
    )


def _temporary(message):
    """'Temporary password for X (user): ABC — share...' -> 'ABC'"""
    return message.split(": ")[1].split(" —")[0]


def test_owner_shows_a_temporary_password_that_works(client, school_a, parent_membership):
    _manager(client, school_a)
    response = _reset(client, parent_membership, follow=True)
    flash = str(list(response.context["messages"])[0])
    temporary = _temporary(flash)

    parent_membership.user.refresh_from_db()
    assert parent_membership.user.must_change_password is True
    assert parent_membership.user.check_password(temporary)
    assert not parent_membership.user.check_password("Parent@1")


def test_reset_is_audited_without_the_password(client, school_a, parent_membership):
    _manager(client, school_a)
    response = _reset(client, parent_membership, follow=True)
    temporary = _temporary(str(list(response.context["messages"])[0]))

    entry = AuditLog.objects.get(action="accounts.password_reset")
    assert entry.target_id == str(parent_membership.user.pk)
    assert temporary not in str(entry.metadata)


def test_admin_may_reset_teacher_or_bursar_are_refused(
    client, school_a, parent_membership,
):
    _manager(client, school_a, role=Membership.Role.ADMIN)
    assert _reset(client, parent_membership).status_code == 302

    _manager(client, school_a, role=Membership.Role.TEACHER)
    assert _reset(client, parent_membership).status_code == 403

    _manager(client, school_a, role=Membership.Role.BURSAR)
    assert _reset(client, parent_membership).status_code == 403


def test_membership_of_another_school_returns_404(
    client, school_a, school_b, parent_membership,
):
    _manager(client, school_b)
    assert _reset(client, parent_membership).status_code == 404


def test_flagged_member_is_kept_on_the_change_page(
    client, school_a, parent_membership,
):
    _manager(client, school_a)
    _reset(client, parent_membership)

    # The reset re-fetched and saved the user in a fresh instance, so the
    # fixture's copy still holds the old password attribute; refresh so the
    # session auth hash matches the real (temporary) password.
    parent_membership.user.refresh_from_db()
    client.force_login(parent_membership.user)
    assert client.get(reverse("core:dashboard")).url == reverse("accounts:force_change")
    assert client.get(reverse("accounts:force_change")).status_code == 200


def test_full_flow_temp_login_weak_refused_strong_accepted(
    client, school_a, parent_membership,
):
    _manager(client, school_a)
    temporary = _temporary(str(list(_reset(client, parent_membership, follow=True).context["messages"])[0]))

    parent_membership.user.refresh_from_db()
    client.force_login(parent_membership.user)
    assert client.get(reverse("core:dashboard")).url == reverse("accounts:force_change")

    weak = client.post(reverse("accounts:force_change"), {
        "new_password1": "parent", "new_password2": "parent",
    })
    assert weak.status_code == 200
    parent_membership.user.refresh_from_db()
    assert parent_membership.user.must_change_password is True

    strong = client.post(reverse("accounts:force_change"), {
        "new_password1": "Ne3w-pass-9", "new_password2": "Ne3w-pass-9",
    })
    assert strong.status_code == 302
    parent_membership.user.refresh_from_db()
    assert parent_membership.user.must_change_password is False
    assert not parent_membership.user.check_password(temporary)
    assert client.get(reverse("core:dashboard")).status_code == 200
    assert AuditLog.objects.filter(action="accounts.password_changed").exists()


def test_mismatched_new_password_changes_nothing(client, school_a, parent_membership):
    parent_membership.user.must_change_password = True
    parent_membership.user.save()
    client.force_login(parent_membership.user)

    client.post(reverse("accounts:force_change"), {
        "new_password1": "Ne3w-pass-9", "new_password2": "Different-1",
    })
    parent_membership.user.refresh_from_db()
    assert parent_membership.user.must_change_password is True


def test_anonymous_gets_the_login_page(client):
    assert client.get(reverse("accounts:force_change")).status_code == 302
