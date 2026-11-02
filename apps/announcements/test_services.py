import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.notifications.models import Notification
from apps.schools.models import Membership

from .models import Announcement
from .services import archive_announcement, create_announcement

pytestmark = pytest.mark.django_db

ALL_ROLES = (
    Membership.Role.OWNER,
    Membership.Role.ADMIN,
    Membership.Role.TEACHER,
    Membership.Role.BURSAR,
    Membership.Role.PARENT,
)


def test_owner_creates_an_audited_active_announcement(school_a, make_request):
    request = make_request(school_a, Membership.Role.OWNER)
    announcement = create_announcement(
        request, title="Mid-term break", body="Next Friday", audience="everyone"
    )
    assert announcement.is_active
    assert announcement.published_by == request.membership
    assert AuditLog.objects.filter(
        school=school_a, action="announcements.announcement_created"
    ).exists()


def test_non_manager_roles_are_refused(school_a, make_request):
    for role in (Membership.Role.TEACHER, Membership.Role.BURSAR, Membership.Role.PARENT):
        request = make_request(school_a, role)
        with pytest.raises(PermissionDenied):
            create_announcement(
                request, title="No", body="no", audience="everyone"
            )
    assert Announcement.objects.count() == 0


def test_everyone_reaches_every_role_but_skips_the_publisher(school_a, make_request, make_member):
    request = make_request(school_a, Membership.Role.OWNER)
    teacher = make_member(school_a, Membership.Role.TEACHER)
    parent = make_member(school_a, Membership.Role.PARENT)
    bursar = make_member(school_a, Membership.Role.BURSAR)
    create_announcement(request, title="Hi", body="hi", audience="everyone")
    recipients = {n.recipient for n in Notification.objects.all()}
    assert recipients == {teacher, parent, bursar}


def test_audience_filters_who_gets_the_bell(school_a, make_request, make_member):
    request = make_request(school_a, Membership.Role.ADMIN)
    teacher = make_member(school_a, Membership.Role.TEACHER)
    parent = make_member(school_a, Membership.Role.PARENT)
    create_announcement(
        request, title="Staff!", body="hi", audience=Announcement.Audience.PARENTS
    )
    recipients = {n.recipient for n in Notification.objects.all()}
    assert recipients == {parent}
    assert teacher not in recipients


def test_inactive_members_and_other_schools_get_nothing(school_a, school_b, make_request, make_member):
    request = make_request(school_a, Membership.Role.OWNER)
    sleepy = make_member(school_a, Membership.Role.TEACHER)
    sleepy.is_active = False
    sleepy.save()
    owner_b = make_member(school_b, Membership.Role.OWNER)
    create_announcement(request, title="Hi", body="hi", audience="everyone")
    recipient_pks = Notification.objects.values_list("recipient", flat=True)
    assert sleepy not in Membership.objects.filter(pk__in=recipient_pks)
    assert owner_b not in Membership.objects.filter(pk__in=recipient_pks)


def test_invalid_audience_is_refused_with_nothing_saved(school_a, make_request):
    request = make_request(school_a, Membership.Role.ADMIN)
    with pytest.raises(ValidationError, match="valid audience"):
        create_announcement(request, title="x", body="x", audience="none")
    assert Announcement.objects.count() == 0
    assert Notification.objects.count() == 0


def test_archive_deactivates_without_deleting(school_a, make_request):
    request = make_request(school_a, Membership.Role.OWNER)
    announcement = create_announcement(
        request, title="Old news", body="x", audience="teachers"
    )
    archived = archive_announcement(request, announcement)
    assert not archived.is_active
    assert Announcement.objects.filter(pk=archived.pk).exists()
    assert AuditLog.objects.filter(
        school=school_a, action="announcements.announcement_archived"
    ).exists()


def test_cannot_archive_another_schools_announcement(school_a, school_b, make_request):
    request_b = make_request(school_b, Membership.Role.OWNER)
    announcement_b = create_announcement(
        request_b, title="Beta", body="x", audience="everyone"
    )
    request_a = make_request(school_a, Membership.Role.ADMIN)
    with pytest.raises(PermissionDenied):
        archive_announcement(request_a, announcement_b)
    announcement_b.refresh_from_db()
    assert announcement_b.is_active
