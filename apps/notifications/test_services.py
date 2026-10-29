import pytest

from .models import Notification
from .services import notify_memberships, unread_count

pytestmark = pytest.mark.django_db


def test_the_actor_does_not_receive_their_own_notification(
    school_a, make_request, make_member
):
    request = make_request(school_a, role="admin")
    created = notify_memberships(
        request, [request.membership],
        kind="results.sheet_sent_back", title="Check this",
    )
    assert created == []
    assert not Notification.objects.exists()


def test_recipients_are_deduplicated(school_a, make_request, make_member):
    request = make_request(school_a, role="admin")
    teacher = make_member(school_a, role="teacher")
    created = notify_memberships(
        request, [teacher, teacher],
        kind="results.sheet_sent_back", title="Check this",
    )
    assert len(created) == 1
    assert Notification.objects.count() == 1


def test_a_recipient_from_another_school_is_skipped(
    school_a, school_b, make_request, make_member
):
    request = make_request(school_a, role="admin")
    stranger = make_member(school_b, role="teacher")
    created = notify_memberships(
        request, [stranger],
        kind="results.sheet_sent_back", title="Check this",
    )
    assert created == []
    assert not Notification.objects.exists()


def test_unread_count_belongs_to_one_membership(
    school_a, make_request, make_member
):
    teacher = make_member(school_a, role="teacher")
    notify_memberships(
        make_request(school_a, role="admin"), [teacher],
        kind="results.sheet_sent_back", title="Check this",
        body="Sent back for correction", url="/results/sheets/1/",
    )
    assert unread_count(make_request(school_a, role="teacher", member=teacher)) == 1
    other = make_request(school_a)  # another member of the same school
    assert unread_count(other) == 0
