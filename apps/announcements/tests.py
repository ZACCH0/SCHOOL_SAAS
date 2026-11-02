import pytest
from django.core.exceptions import ValidationError

from apps.schools.models import Membership

from .models import Announcement

pytestmark = pytest.mark.django_db


def make_announcement(school, member, **kwargs):
    defaults = {
        "school": school,
        "title": "PTA meeting",
        "body": "The PTA holds its term meeting on Friday.",
        "published_by": member,
    }
    defaults.update(kwargs)
    return Announcement.objects.create(**defaults)


def test_default_audience_is_everyone(school_a, make_member):
    owner = make_member(school_a, Membership.Role.OWNER)
    announcement = make_announcement(school_a, owner)
    assert announcement.audience == Announcement.Audience.EVERYONE
    assert announcement.is_active
    assert str(announcement) == "PTA meeting"


def test_teacher_cannot_publish(school_a, make_member):
    teacher = make_member(school_a, Membership.Role.TEACHER)
    with pytest.raises(ValidationError, match="owner or an admin"):
        make_announcement(school_a, teacher)


def test_published_by_foreign_membership_rejected(school_a, school_b, make_member):
    owner_a = make_member(school_a, Membership.Role.OWNER)
    owner_b = make_member(school_b, Membership.Role.OWNER)
    with pytest.raises(ValidationError, match="different school"):
        make_announcement(school_b, owner_a)
    with pytest.raises(ValidationError, match="different school"):
        make_announcement(school_a, owner_b)


def test_school_a_cannot_read_school_b_announcement_by_id(school_a, school_b, make_member):
    owner_b = make_member(school_b, Membership.Role.OWNER)
    announcement = make_announcement(school_b, owner_b, title="Beta only notice")
    owner_a = make_member(school_a, Membership.Role.OWNER)

    assert announcement not in Announcement.objects.for_school(school_a)
    with pytest.raises(Announcement.DoesNotExist):
        Announcement.objects.for_school(school_a).get(pk=announcement.pk)


def test_bursar_cannot_publish_but_owner_admin_can(school_a, make_member):
    bursar = make_member(school_a, Membership.Role.BURSAR)
    with pytest.raises(ValidationError, match="owner or an admin"):
        make_announcement(school_a, bursar)
    admin_a = make_member(school_a, Membership.Role.ADMIN)
    announcement = make_announcement(school_a, admin_a, audience=Announcement.Audience.TEACHERS)
    assert announcement.audience == Announcement.Audience.TEACHERS
