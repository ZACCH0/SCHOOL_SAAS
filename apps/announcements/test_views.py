import pytest

from apps.announcements.models import Announcement
from apps.announcements.services import create_announcement
from apps.audit.models import AuditLog
from apps.schools.models import Membership

pytestmark = pytest.mark.django_db

LIST_URL = "/announcements/"
CREATE_URL = "/announcements/new/"


def _request(school, member):
    from django.test import RequestFactory
    request = RequestFactory().get("/")
    request.user = member.user
    request.membership = member
    request.school = school
    return request


def publish(school, member, title="PTA meeting", audience="everyone", body="Friday"):
    return create_announcement(
        _request(school, member), title=title, body=body, audience=audience
    )


def _request(school, member):
    from django.test import RequestFactory
    request = RequestFactory().get("/")
    request.user = member.user
    request.membership = member
    request.school = school
    return request


def test_list_requires_login(client):
    response = client.get(LIST_URL)
    assert response.status_code == 302
    assert "/accounts/login/" in response.url


def test_owner_sees_all_notices_and_can_create(client, school_a, login_as):
    owner = login_as(school_a, Membership.Role.OWNER)
    publish(school_a, owner, title="Break notice")
    publish(school_a, owner, title="Teacher only", audience="teachers")
    response = client.get(LIST_URL)
    assert response.status_code == 200
    assert b"Break notice" in response.content
    assert b"Teacher only" in response.content


def test_teacher_sees_everyone_and_teachers_only(client, school_a, login_as):
    owner = login_as(school_a, Membership.Role.OWNER)
    publish(school_a, owner, title="Everybody")
    publish(school_a, owner, title="Parents only", audience="parents")
    login_as(school_a, Membership.Role.TEACHER)
    response = client.get(LIST_URL)
    assert response.status_code == 200
    content = response.content
    assert b"Everybody" in content
    assert b"Parents only" not in content


def test_parent_never_sees_teacher_notices(client, school_a, login_as):
    owner_anon = login_as(school_a, Membership.Role.OWNER)
    publish(school_a, owner_anon, title="Staff briefing", audience="staff")
    login_as(school_a, Membership.Role.PARENT)
    response = client.get(LIST_URL)
    assert b"Staff briefing" not in response.content


def test_archived_notice_disappears_from_the_board(client, school_a, login_as):
    owner = login_as(school_a, Membership.Role.OWNER)
    announcement = publish(school_a, owner, title="Old notice")
    archiver = login_as(school_a, Membership.Role.ADMIN)
    response = client.post(f"/announcements/{announcement.pk}/archive/")
    assert response.status_code == 302
    archiver.refresh_from_db()
    response = client.get(LIST_URL)
    assert b"Old notice" not in response.content
    assert Announcement.objects.filter(pk=announcement.pk).exists()


def test_teacher_gets_403_on_archive_and_create(school_a, login_as, make_member, client):
    owner_member = make_member(school_a, Membership.Role.OWNER)
    announcement = publish(school_a, owner_member, title="Keep")
    teacher = login_as(school_a, Membership.Role.TEACHER)
    assert client.get(CREATE_URL).status_code == 403
    assert client.post(f"/announcements/{announcement.pk}/archive/").status_code == 403
    assert AuditLog.objects.filter(action="announcements.announcement_archived").count() == 0


def test_bursar_sees_staff_notices(client, school_a, login_as):
    owner = login_as(school_a, Membership.Role.OWNER)
    publish(school_a, owner, title="Entrance duty", audience="staff")
    login_as(school_a, Membership.Role.BURSAR)
    response = client.get(LIST_URL)
    assert b"Entrance duty" in response.content


def test_create_page_posts_and_audits(client, school_a, login_as):
    login_as(school_a, Membership.Role.ADMIN)
    response = client.post(
        CREATE_URL,
        {"title": "Exam week", "body": "Starts Monday.", "audience": "everyone"},
    )
    assert response.status_code == 302
    assert Announcement.objects.filter(title="Exam week", audience="everyone").exists()
    assert AuditLog.objects.filter(action="announcements.announcement_created").exists()


def test_foreign_school_notice_is_404_for_archive(client, school_a, school_b, login_as, make_member):
    owner_b = make_member(school_b, Membership.Role.OWNER)
    announcement_b = publish(school_b, owner_b, title="Beta notice")
    login_as(school_a, Membership.Role.OWNER)
    response = client.post(f"/announcements/{announcement_b.pk}/archive/")
    assert response.status_code == 404
