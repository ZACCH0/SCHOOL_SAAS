from datetime import date
import pytest
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.core.exceptions import PermissionDenied
from django.http import Http404, HttpResponse
from django.test import RequestFactory
from django.views import View
from django.views.generic import DetailView
from apps.academics.models import AcademicSession
from .lookups import SchoolScopedMixin, get_for_school_or_404
from .models import Membership, School
from .permissions import RoleRequiredMixin

User = get_user_model()
Role = Membership.Role

def make_session(school, name="2026/2027"):
    return AcademicSession.objects.create(
        school=school, name=name, start_date=date(2026, 9, 1), end_date=date(2027, 7, 31)
    )

def make_request(school=None, role=None, user=None):
    request = RequestFactory().get("/")
    request.school = school
    request.user = user or AnonymousUser()
    request.membership = None
    if school is not None and role is not None:
        person = User.objects.create_user(f"u-{role}-{school.pk}", password="S3cure-pass!")
        request.user = person
        request.membership = Membership.objects.create(user=person, school=school, role=role)
    return request

@pytest.fixture
def school_a():
    return School.objects.create(name="Alpha School", slug="alpha")

@pytest.fixture
def school_b():
    return School.objects.create(name="Beta School", slug="beta")

@pytest.mark.django_db
def test_returns_own_schools_record(school_a):
    session = make_session(school_a)
    request = make_request(school_a)
    assert get_for_school_or_404(AcademicSession, request, pk=session.pk) == session

@pytest.mark.django_db
def test_other_schools_record_is_404(school_a, school_b):
    foreign = make_session(school_b)
    with pytest.raises(Http404):
        get_for_school_or_404(AcademicSession, make_request(school_a), pk=foreign.pk)

@pytest.mark.django_db
def test_no_active_school_is_404(school_a):
    session = make_session(school_a)
    with pytest.raises(Http404):
        get_for_school_or_404(AcademicSession, make_request(None), pk=session.pk)

@pytest.mark.django_db
def test_accepts_a_queryset(school_a):
    session = make_session(school_a)
    queryset = AcademicSession.objects.filter(name="2026/2027")
    assert get_for_school_or_404(queryset, make_request(school_a), pk=session.pk) == session

class SessionDetail(SchoolScopedMixin, DetailView):
    model = AcademicSession
    template_name = "components/page_header.html"

@pytest.mark.django_db
def test_scoped_view_serves_own_record(school_a):
    session = make_session(school_a)
    response = SessionDetail.as_view()(make_request(school_a), pk=session.pk)
    assert response.status_code == 200

@pytest.mark.django_db
def test_scoped_view_hides_other_schools_record(school_a, school_b):
    foreign = make_session(school_b)
    with pytest.raises(Http404):
        SessionDetail.as_view()(make_request(school_a), pk=foreign.pk)

class AdminOnly(RoleRequiredMixin, View):
    allowed_roles = (Role.ADMIN,)
    def get(self, request):
        return HttpResponse("ok")

@pytest.mark.django_db
def test_role_mixin_allows_listed_role(school_a):
    response = AdminOnly.as_view()(make_request(school_a, Role.ADMIN))
    assert response.status_code == 200

@pytest.mark.django_db
def test_role_mixin_denies_other_role(school_a):
    with pytest.raises(PermissionDenied):
        AdminOnly.as_view()(make_request(school_a, Role.TEACHER))

def test_role_mixin_redirects_anonymous_to_login():
    response = AdminOnly.as_view()(make_request(None))
    assert response.status_code == 302