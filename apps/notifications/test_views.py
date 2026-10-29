import pytest
from django.urls import reverse

from .models import Notification

pytestmark = pytest.mark.django_db


def _note(school_a, membership, title="A note", read=False):
    return Notification.objects.create(
        school=school_a, recipient=membership, kind="results.sheet_sent_back",
        title=title, body="Body text", url="/results/sheets/1/", is_read=read,
    )


def test_the_list_requires_login(client):
    assert client.get(reverse("notifications:list")).status_code == 302


def test_a_member_sees_only_their_own_notifications(
    client, school_a, school_b, make_member, login_as
):
    member = login_as(school_a, role="teacher")
    colleague = make_member(school_a, role="teacher")
    other_school = make_member(school_b, role="teacher")
    _note(school_a, member, title="Mine visible")
    _note(school_a, colleague, title="Someone else's")
    _note(school_b, other_school, title="Another school's")

    response = client.get(reverse("notifications:list"))
    content = response.content
    assert b"Mine visible" in content
    assert b"Someone else's" not in content
    assert b"Another school's" not in content


def test_the_unread_badge_clears_after_marking_read(
    client, school_a, make_member, login_as
):
    member = login_as(school_a, role="teacher")
    note = _note(school_a, member)
    response = client.get(reverse("notifications:list"))
    assert response.context["unread_notifications"] == 1

    client.post(reverse("notifications:mark_read", args=[note.pk]))
    response = client.get(reverse("notifications:list"))
    assert response.context["unread_notifications"] == 0
    note.refresh_from_db()
    assert note.is_read


def test_mark_read_ignores_another_members_note(
    client, school_a, make_member, login_as
):
    login_as(school_a, role="teacher")
    stranger = make_member(school_a, role="owner")
    note = _note(school_a, stranger)
    client.post(reverse("notifications:mark_read", args=[note.pk]))
    note.refresh_from_db()
    assert note.is_read is False


def test_mark_all_read_and_an_empty_list(
    client, school_a, make_member, login_as
):
    member = login_as(school_a, role="owner")
    _note(school_a, member, title="One")
    _note(school_a, member, title="Two", read=True)
    client.post(reverse("notifications:mark_all_read"))
    assert Notification.objects.filter(is_read=False).count() == 0


def test_a_foreign_note_id_does_not_crash(client, school_a, school_b, make_member, login_as):
    login_as(school_a, role="teacher")
    stranger = make_member(school_b, role="teacher")
    note = _note(school_b, stranger)
    client.post(reverse("notifications:mark_read", args=[note.pk]))
    assert Notification.objects.filter(is_read=False).count() == 1
