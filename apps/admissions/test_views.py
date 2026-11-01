from datetime import date

import pytest
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.classes.models import Level, SchoolClass
from apps.students.models import Student

from .models import Applicant
from .services import review_applicant, decide_applicant

pytestmark = pytest.mark.django_db

LIST_URL = reverse("admissions:list")
CREATE_URL = reverse("admissions:create")


@pytest.fixture
def class_a(school_a):
    level = Level.objects.create(school=school_a, name="Primary", order=1)
    return SchoolClass.objects.create(
        school=school_a, level=level, name="Primary 1", order=1
    )


@pytest.fixture
def manager(make_member, school_a):
    return make_member(school_a, role=make_member.__defaults__[0])


def _login(client, membership):
    client.force_login(membership.user)


def test_login_needed_anonymous_gets_login_page(client):
    response = client.get(LIST_URL)
    assert response.status_code == 302
    assert response.url.startswith("/accounts/login/")


def test_teacher_and_bursar_get_403(client, make_member, school_a):
    for role in ("teacher", "bursar", "parent"):
        member = make_member(school_a, role=role)
        _login(client, member)
        assert client.get(LIST_URL).status_code == 403


def test_list_only_shows_active_school_applicants(client, make_member, school_a, school_b):
    Applicant.objects.create(
        school=school_a, reference="APP-0001", first_name="Bola",
        last_name="Ade", sex="male",
    )
    foreign = Applicant.objects.create(
        school=school_b, reference="APP-XXXX", first_name="Chike",
        last_name="Oke", sex="male",
    )
    _login(client, make_member(school_a, role="owner"))
    content = client.get(LIST_URL).content.decode()
    assert "APP-0001" in content
    assert "APP-XXXX" not in content
    assert (
        client.get(reverse("admissions:detail", args=[foreign.pk])).status_code
        == 404
    )


def test_create_applicant_assigns_reference_and_audits(client, make_member, school_a):
    _login(client, make_member(school_a, role="owner"))
    response = client.post(
        CREATE_URL,
        {
            "first_name": "Bola", "last_name": "Ade", "sex": "male",
            "date_of_birth": "2018-05-10",
            "guardian_name": "Mama Bola",
        },
        follow=True,
    )
    applicant = Applicant.objects.for_school(school_a).latest("id")
    assert applicant.reference == "APP-0001"
    assert applicant.status == Applicant.Status.APPLIED
    assert f"Application {applicant.reference}" in str(
        list(response.context["messages"])
    )
    assert AuditLog.objects.filter(
        action="admissions.applicant_created"
    ).latest("id").target_id == str(applicant.pk)


def test_create_form_stays_on_validation_error(client, make_member, school_a):
    _login(client, make_member(school_a, role="owner"))
    response = client.post(CREATE_URL, {"first_name": "", "last_name": "", "sex": "male"})
    assert response.status_code == 200
    assert not Applicant.objects.exists()


def test_detail_page_shows_the_next_action_per_status(client, make_member, school_a):
    _login(client, make_member(school_a, role="owner"))
    applicant = Applicant.objects.create(
        school=school_a, reference="APP-0002", first_name="Bola",
        last_name="Ade", sex="male",
    )
    detail_url = reverse("admissions:detail", args=[applicant.pk])

    content = client.get(detail_url).content.decode()
    assert "Mark as reviewed" in content

    client.post(
        reverse("admissions:review", args=[applicant.pk]), {"notes": "Interview 12 Nov"},
        follow=True,
    )
    applicant.refresh_from_db()
    assert applicant.status == Applicant.Status.REVIEWED
    content = client.get(detail_url).content.decode()
    assert "Admit" in content and "Decline" in content


def test_decide_admit_then_convert_creates_a_student(
    client, make_member, school_a, class_a,
):
    _login(client, make_member(school_a, role="owner"))
    applicant = Applicant.objects.create(
        school=school_a, reference="APP-0003", first_name="Bola",
        last_name="Ade", sex="male", target_class=class_a,
        date_of_birth=date(2018, 5, 10),
    )
    decide_url = reverse("admissions:decide", args=[applicant.pk])
    client.post(reverse("admissions:review", args=[applicant.pk]), {"notes": ""})
    response = client.post(
        decide_url, {"decision": "admit", "notes": ""}, follow=True,
    )
    applicant.refresh_from_db()
    assert applicant.status == Applicant.Status.ADMITTED
    assert b"Enrol this applicant" in response.content

    convert_url = reverse("admissions:convert", args=[applicant.pk])
    convert_page = client.get(convert_url)
    assert convert_page.status_code == 200
    assert b"admission_number" in convert_page.content

    response = client.post(
        convert_url, {"admission_number": "FSS/2026/300"}, follow=True,
    )
    assert response.request["PATH_INFO"] == "/students/"
    student = Student.objects.get(admission_number="FSS/2026/300")
    assert student.current_class == class_a

    applicant.refresh_from_db()
    assert applicant.status == Applicant.Status.CONVERTED
    assert applicant.converted_student == student


def test_decide_decline_keeps_no_conversion_button(client, make_member, school_a):
    _login(client, make_member(school_a, role="owner"))
    applicant = Applicant.objects.create(
        school=school_a, reference="APP-0004", first_name="Bola",
        last_name="Ade", sex="male",
    )
    client.post(
        reverse("admissions:review", args=[applicant.pk]), {"notes": ""},
    )
    client.post(
        reverse("admissions:decide", args=[applicant.pk]),
        {"decision": "decline", "notes": "No placement"},
        follow=True,
    )
    applicant.refresh_from_db()
    assert applicant.status == Applicant.Status.DECLINED
    content = client.get(
        reverse("admissions:detail", args=[applicant.pk])
    ).content.decode()
    assert "Enrol" not in content


def test_results_of_decide_when_a_second_manager_is_a_foreign_school(client, make_member, school_a, school_b):
    membership_b = make_member(school_b, role="owner")
    _login(client, membership_b)
    applicant = Applicant.objects.create(
        school=school_a, reference="APP-0005", first_name="Bola",
        last_name="Ade", sex="male",
    )
    for action in ("review", "decide"):
        assert (
            client.post(
                reverse(f"admissions:{action}", args=[applicant.pk]),
                {"decision": "admit", "notes": ""},
            ).status_code
            == 404
        )
    assert AuditLog.objects.filter(target_id=applicant.pk).count() == 0
