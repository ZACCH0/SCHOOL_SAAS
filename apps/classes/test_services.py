import pytest
from django.core.exceptions import PermissionDenied, ValidationError

from apps.audit.models import AuditLog
from apps.schools.models import Membership

from .models import Level, SchoolClass
from .services import (
    add_section, assign_class_teacher, create_class, set_class_active, update_class,
)

Role = Membership.Role


@pytest.fixture
def level(school_a):
    return Level.objects.create(school=school_a, name="Primary", order=1)


@pytest.fixture
def primary_four(school_a, level):
    return SchoolClass.objects.create(school=school_a, level=level, name="Primary 4", order=4)


@pytest.mark.django_db
def test_admin_creates_a_class_and_it_is_audited(school_a, level, make_request):
    request = make_request(school_a)
    school_class = create_class(request, level=level, name="  Primary 4 ", order=4)
    assert school_class.name == "Primary 4" and school_class.school == school_a
    entry = AuditLog.objects.get(action="class.created")
    assert entry.school == school_a and entry.actor == request.user
    assert entry.target_repr == "Primary 4"


@pytest.mark.django_db
def test_a_teacher_cannot_create_a_class(school_a, level, make_request):
    with pytest.raises(PermissionDenied):
        create_class(make_request(school_a, Role.TEACHER), level=level, name="X", order=1)
    assert not SchoolClass.objects.exists() and not AuditLog.objects.exists()


@pytest.mark.django_db
def test_duplicate_class_gives_a_friendly_error_and_no_audit(school_a, level, make_request):
    request = make_request(school_a)
    create_class(request, level=level, name="Primary 4", order=4)
    with pytest.raises(ValidationError):
        create_class(request, level=level, name="primary 4", order=5)
    assert AuditLog.objects.filter(action="class.created").count() == 1


@pytest.mark.django_db
def test_blank_class_name_is_refused(school_a, level, make_request):
    with pytest.raises(ValidationError):
        create_class(make_request(school_a), level=level, name="   ", order=1)


@pytest.mark.django_db
def test_a_level_from_another_school_is_refused(school_a, school_b, make_request):
    foreign_level = Level.objects.create(school=school_b, name="Primary", order=1)
    with pytest.raises(PermissionDenied):
        create_class(make_request(school_a), level=foreign_level, name="X", order=1)


@pytest.mark.django_db
def test_update_class_records_what_changed(primary_four, school_a, make_request):
    update_class(make_request(school_a), primary_four, name="Primary Four", order=9)
    entry = AuditLog.objects.get(action="class.updated")
    assert entry.metadata["changes"] == {
        "name": ["Primary 4", "Primary Four"], "order": [4, 9],
    }


@pytest.mark.django_db
def test_update_with_no_change_writes_no_audit_entry(primary_four, school_a, make_request):
    update_class(make_request(school_a), primary_four, name="Primary 4")
    assert not AuditLog.objects.filter(action="class.updated").exists()


@pytest.mark.django_db
def test_another_schools_admin_cannot_update_a_class(primary_four, school_b, make_request):
    with pytest.raises(PermissionDenied):
        update_class(make_request(school_b), primary_four, name="Hacked")
    primary_four.refresh_from_db()
    assert primary_four.name == "Primary 4"


@pytest.mark.django_db
def test_classes_are_archived_not_deleted(primary_four, school_a, make_request):
    request = make_request(school_a)
    set_class_active(request, primary_four, False)
    set_class_active(request, primary_four, True)
    actions = list(AuditLog.objects.order_by("id").values_list("action", flat=True))
    assert actions == ["class.deactivated", "class.activated"]


@pytest.mark.django_db
def test_add_section_and_reject_duplicates(primary_four, school_a, make_request):
    request = make_request(school_a)
    add_section(request, primary_four, "A")
    assert AuditLog.objects.filter(action="section.created").count() == 1
    with pytest.raises(ValidationError):
        add_section(request, primary_four, "a")


@pytest.mark.django_db
def test_class_teacher_is_assigned_then_changed(
    primary_four, school_a, make_request, make_member, make_session
):
    request = make_request(school_a)
    session, first, second = make_session(school_a), make_member(school_a), make_member(school_a)
    assign_class_teacher(request, school_class=primary_four, session=session, teacher=first)
    assign_class_teacher(request, school_class=primary_four, session=session, teacher=first)
    assign_class_teacher(request, school_class=primary_four, session=session, teacher=second)
    actions = list(AuditLog.objects.order_by("id").values_list("action", flat=True))
    assert actions == ["class_teacher.assigned", "class_teacher.changed"]


@pytest.mark.django_db
def test_class_teacher_must_have_the_teacher_role(
    primary_four, school_a, make_request, make_member, make_session
):
    bursar = make_member(school_a, Role.BURSAR)
    with pytest.raises(ValidationError):
        assign_class_teacher(
            make_request(school_a), school_class=primary_four,
            session=make_session(school_a), teacher=bursar,
        )
