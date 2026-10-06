import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import HttpResponse
from django.test import RequestFactory

from .middleware import SESSION_KEY, ActiveSchoolMiddleware
from .models import Membership, School
from .permissions import role_required

User = get_user_model()
Role = Membership.Role

def make_request(user, session=None):
    request = RequestFactory().get("/")
    request.user = user
    request.session = session if session is not None else {}
    return request

def run_middleware(request):
    ActiveSchoolMiddleware(lambda r: HttpResponse("ok"))(request)
    return request

def join(user, school, role=Role.TEACHER, **extra):
    return Membership.objects.create(user=user, school=school, role=role, **extra)

@pytest.fixture
def school_a():
    return School.objects.create(name="Alpha School", slug="alpha")

@pytest.fixture
def school_b():
    return School.objects.create(name="Beta School", slug="beta")

@pytest.fixture
def user():
    return User.objects.create_user("teacher1", password="S3cure-pass!")

def test_anonymous_user_has_no_school():
    request = run_middleware(make_request(AnonymousUser()))
    assert request.membership is None
    assert request.school is None

@pytest.mark.django_db
def test_user_without_membership_has_no_school(user):
    request = run_middleware(make_request(user))
    assert request.school is None

@pytest.mark.django_db
def test_single_membership_is_selected_automatically(user, school_a):
    membership = join(user, school_a)
    request = run_middleware(make_request(user))
    assert request.membership == membership
    assert request.school == school_a

@pytest.mark.django_db
def test_multiple_memberships_need_a_choice(user, school_a, school_b):
    join(user, school_a)
    join(user, school_b)
    request = run_middleware(make_request(user))
    assert request.membership is None

@pytest.mark.django_db
def test_chosen_membership_is_used(user, school_a, school_b):
    join(user, school_a)
    chosen = join(user, school_b)
    request = run_middleware(make_request(user, {SESSION_KEY: chosen.pk}))
    assert request.school == school_b

@pytest.mark.django_db
def test_cannot_select_another_users_membership(user, school_a, school_b):
    other = User.objects.create_user("other", password="S3cure-pass!")
    foreign = join(other, school_b)
    join(user, school_a)
    join(user, school_a, Role.PARENT)
    request = run_middleware(make_request(user, {SESSION_KEY: foreign.pk}))
    assert request.membership is None
    assert request.school is None

@pytest.mark.django_db
def test_inactive_membership_is_ignored(user, school_a):
    join(user, school_a, is_active=False)
    request = run_middleware(make_request(user))
    assert request.school is None

@pytest.mark.django_db
def test_inactive_school_is_ignored(user, school_a):
    join(user, school_a)
    school_a.is_active = False
    school_a.save()
    request = run_middleware(make_request(user))
    assert request.school is None

@role_required(Role.ADMIN, Role.OWNER)
def admin_only_view(request):
    return HttpResponse("ok")

@pytest.mark.django_db
def test_role_required_allows_permitted_role(user, school_a):
    join(user, school_a, Role.ADMIN)
    request = run_middleware(make_request(user))
    assert admin_only_view(request).status_code == 200

@pytest.mark.django_db
def test_role_required_denies_other_role(user, school_a):
    join(user, school_a, Role.TEACHER)
    request = run_middleware(make_request(user))
    with pytest.raises(PermissionDenied):
        admin_only_view(request)

@pytest.mark.django_db
def test_role_required_denies_user_without_membership(user):
    request = run_middleware(make_request(user))
    with pytest.raises(PermissionDenied):
        admin_only_view(request)

def test_role_required_redirects_anonymous_to_login():
    request = run_middleware(make_request(AnonymousUser()))
    assert admin_only_view(request).status_code == 302