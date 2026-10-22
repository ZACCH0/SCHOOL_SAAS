import pytest
from django.contrib.auth import get_user_model
from django.test import RequestFactory
from django.urls import reverse
from apps.schools.models import Membership, School
from .models import AuditLog, AuditLogImmutable
from .services import record

User = get_user_model()
GOOD = "S3cure-pass!"

@pytest.fixture
def school_a():
    return School.objects.create(name="Alpha School", slug="alpha")

@pytest.fixture
def school_b():
    return School.objects.create(name="Beta School", slug="beta")

@pytest.fixture
def teacher():
    return User.objects.create_user("teacher1", password=GOOD)

def make_request(user=None, school=None, ip="10.0.0.5"):
    request = RequestFactory().get("/", REMOTE_ADDR=ip)
    request.user = user
    request.school = school
    return request

@pytest.mark.django_db
def test_record_stores_who_what_where(teacher, school_a):
    entry = record(
        make_request(teacher, school_a), "school.updated", target=school_a, field="name"
    )
    assert entry.actor == teacher and entry.actor_label == "teacher1"
    assert entry.school == school_a
    assert entry.action == "school.updated"
    assert entry.target_type == "schools.School"
    assert entry.target_id == str(school_a.pk)
    assert entry.target_repr == "Alpha School"
    assert entry.metadata == {"field": "name"}

@pytest.mark.django_db
def test_record_captures_ip_address(teacher, school_a):
    entry = record(make_request(teacher, school_a, ip="10.0.0.5"), "x.y")
    assert entry.ip_address == "10.0.0.5"

@pytest.mark.django_db
def test_anonymous_actor_is_stored_as_empty(school_a):
    from django.contrib.auth.models import AnonymousUser

    entry = record(make_request(AnonymousUser(), school_a), "x.y")
    assert entry.actor is None and entry.actor_label == ""

@pytest.mark.django_db
def test_entries_cannot_be_edited(teacher, school_a):
    entry = record(make_request(teacher, school_a), "x.y")
    entry.action = "tampered"
    with pytest.raises(AuditLogImmutable):
        entry.save()

@pytest.mark.django_db
def test_entries_cannot_be_deleted(teacher, school_a):
    entry = record(make_request(teacher, school_a), "x.y")
    with pytest.raises(AuditLogImmutable):
        entry.delete()
    with pytest.raises(AuditLogImmutable):
        AuditLog.objects.all().delete()
    with pytest.raises(AuditLogImmutable):
        AuditLog.objects.all().update(action="tampered")

@pytest.mark.django_db
def test_for_school_only_returns_that_schools_entries(teacher, school_a, school_b):
    mine = record(make_request(teacher, school_a), "x.y")
    record(make_request(teacher, school_b), "x.y")
    assert list(AuditLog.objects.for_school(school_a)) == [mine]

@pytest.mark.django_db
def test_login_is_recorded_with_the_users_school(client, teacher, school_a):
    Membership.objects.create(user=teacher, school=school_a, role=Membership.Role.TEACHER)
    client.post(reverse("accounts:login"), {"username": "teacher1", "password": GOOD})
    entry = AuditLog.objects.get(action="auth.login")
    assert entry.actor == teacher and entry.school == school_a

@pytest.mark.django_db
def test_logout_is_recorded(client, teacher):
    client.force_login(teacher)
    client.post(reverse("accounts:logout"))
    assert AuditLog.objects.filter(action="auth.logout", actor=teacher).count() == 1

@pytest.mark.django_db
def test_failed_login_is_not_written_as_a_login(client, teacher):
    client.post(reverse("accounts:login"), {"username": "teacher1", "password": "wrong"})
    assert not AuditLog.objects.filter(action="auth.login").exists()

@pytest.mark.django_db
def test_admin_cannot_add_audit_entries(client):
    root = User.objects.create_superuser("root", password=GOOD)
    client.force_login(root)
    assert client.get(reverse("admin:audit_auditlog_add")).status_code == 403