import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.classes.models import Level, SchoolClass
from apps.schools.models import Membership

from .models import ClassSubject, Subject, TeacherAssignment
from .services import (
    add_subject_to_class, assign_teacher, create_subject, remove_subject_from_class,
    set_subject_active, unassign_teacher,
)

Role = Membership.Role


@pytest.fixture
def primary_four(school_a):
    level = Level.objects.create(school=school_a, name="Primary", order=1)
    return SchoolClass.objects.create(school=school_a, level=level, name="Primary 4", order=4)


@pytest.fixture
def maths(school_a):
    return Subject.objects.create(school=school_a, name="Mathematics")


@pytest.fixture
def taught_class(primary_four, maths, school_a, make_request):
    add_subject_to_class(make_request(school_a), primary_four, maths)
    return primary_four


def actions():
    return list(AuditLog.objects.order_by("id").values_list("action", flat=True))


@pytest.mark.django_db
def test_admin_creates_a_subject_and_it_is_audited(school_a, make_request):
    subject = create_subject(make_request(school_a), name=" Biology ", code="BIO")
    assert subject.name == "Biology" and subject.code == "BIO"
    assert actions() == ["subject.created"]


@pytest.mark.django_db
def test_duplicate_subject_name_gives_a_friendly_error(school_a, make_request):
    request = make_request(school_a)
    create_subject(request, name="Biology")
    with pytest.raises(ValidationError):
        create_subject(request, name="biology")


@pytest.mark.django_db
def test_a_teacher_cannot_create_a_subject(school_a, make_request):
    with pytest.raises(PermissionDenied):
        create_subject(make_request(school_a, Role.TEACHER), name="Biology")


@pytest.mark.django_db
def test_subjects_are_archived_not_deleted(maths, school_a, make_request):
    set_subject_active(make_request(school_a), maths, False)
    maths.refresh_from_db()
    assert maths.is_active is False
    assert actions() == ["subject.deactivated"]


@pytest.mark.django_db
def test_adding_a_subject_twice_to_a_class_is_refused(taught_class, maths, school_a, make_request):
    with pytest.raises(ValidationError):
        add_subject_to_class(make_request(school_a), taught_class, maths)
    assert actions() == ["class_subject.added"]


@pytest.mark.django_db
def test_subject_cannot_be_removed_while_a_teacher_is_assigned(
    taught_class, maths, school_a, make_request, make_member, make_session
):
    request = make_request(school_a)
    assign_teacher(
        request, school_class=taught_class, subject=maths,
        teacher=make_member(school_a), session=make_session(school_a),
    )
    with pytest.raises(ValidationError):
        remove_subject_from_class(request, taught_class, maths)
    assert ClassSubject.objects.count() == 1


@pytest.mark.django_db
def test_unused_subject_can_be_removed_from_a_class(taught_class, maths, school_a, make_request):
    remove_subject_from_class(make_request(school_a), taught_class, maths)
    assert not ClassSubject.objects.exists()
    assert actions() == ["class_subject.added", "class_subject.removed"]


@pytest.mark.django_db
def test_teacher_is_assigned_then_reassigned(
    taught_class, maths, school_a, make_request, make_member, make_session
):
    request = make_request(school_a)
    session, first, second = make_session(school_a), make_member(school_a), make_member(school_a)
    kwargs = {"school_class": taught_class, "subject": maths, "session": session}
    assign_teacher(request, teacher=first, **kwargs)
    assign_teacher(request, teacher=first, **kwargs)  # same teacher: nothing new
    assign_teacher(request, teacher=second, **kwargs)
    assert actions()[1:] == ["teacher.assigned", "teacher.reassigned"]
    assert TeacherAssignment.objects.get().teacher == second


@pytest.mark.django_db
def test_only_owner_or_admin_can_assign_teachers(
    taught_class, maths, school_a, make_request, make_member, make_session
):
    with pytest.raises(PermissionDenied):
        assign_teacher(
            make_request(school_a, Role.TEACHER), school_class=taught_class, subject=maths,
            teacher=make_member(school_a), session=make_session(school_a),
        )


@pytest.mark.django_db
def test_a_teacher_from_another_school_is_refused(
    taught_class, maths, school_a, school_b, make_request, make_member, make_session
):
    with pytest.raises(PermissionDenied):
        assign_teacher(
            make_request(school_a), school_class=taught_class, subject=maths,
            teacher=make_member(school_b), session=make_session(school_a),
        )


@pytest.mark.django_db
def test_unassigning_a_teacher_is_audited(
    taught_class, maths, school_a, make_request, make_member, make_session
):
    request = make_request(school_a)
    assignment = assign_teacher(
        request, school_class=taught_class, subject=maths,
        teacher=make_member(school_a), session=make_session(school_a),
    )
    unassign_teacher(request, assignment)
    assert not TeacherAssignment.objects.exists()
    assert actions()[-1] == "teacher.unassigned"
