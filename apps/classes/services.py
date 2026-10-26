from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import record
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, require_role
from apps.schools.service_helpers import ensure_owned, save_or_explain

from .models import ClassTeacher, Level, SchoolClass, Section

STANDARD_STRUCTURE = [
    ("Primary", True, ["Primary 1", "Primary 2", "Primary 3", "Primary 4", "Primary 5", "Primary 6"]),
    ("Junior Secondary", False, ["JSS 1", "JSS 2", "JSS 3"]),
    ("Senior Secondary", False, ["SS 1", "SS 2", "SS 3"]),
]


def _name(value):
    value = (value or "").strip()
    if not value:
        raise ValidationError("A name is required.")
    return value


@transaction.atomic
def seed_standard_structure(school):
    """Create the usual Nigerian levels and classes for a NEW school.

    Only Primary is switched on. Everything can be renamed, switched on or off later.
    Does nothing (returns False) if the school already has classes.
    """
    if SchoolClass.objects.for_school(school).exists():
        return False
    order = 0
    for level_order, (level_name, active, class_names) in enumerate(STANDARD_STRUCTURE, start=1):
        level = Level.objects.create(
            school=school, name=level_name, order=level_order, is_active=active
        )
        for class_name in class_names:
            order += 1
            SchoolClass.objects.create(
                school=school, level=level, name=class_name, order=order, is_active=active
            )
    return True


@transaction.atomic
def create_class(request, *, level, name, order):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, level)
    school_class = save_or_explain(
        SchoolClass(school=request.school, level=level, name=_name(name), order=order),
        "A class with that name or position already exists.",
    )
    record(request, "class.created", target=school_class, level=level.name)
    return school_class


@transaction.atomic
def update_class(request, school_class, *, name=None, level=None, order=None):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, school_class, *([level] if level else []))
    changes = {}
    if name is not None:
        new_name = _name(name)
        if new_name != school_class.name:
            changes["name"] = [school_class.name, new_name]
            school_class.name = new_name
    if level is not None and level.pk != school_class.level_id:
        changes["level"] = [school_class.level.name, level.name]
        school_class.level = level
    if order is not None and order != school_class.order:
        changes["order"] = [school_class.order, order]
        school_class.order = order
    if changes:
        save_or_explain(school_class, "A class with that name or position already exists.")
        record(request, "class.updated", target=school_class, changes=changes)
    return school_class


@transaction.atomic
def set_class_active(request, school_class, active):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, school_class)
    if school_class.is_active != active:
        school_class.is_active = active
        save_or_explain(school_class, "Could not save the class.")
        record(request, "class.activated" if active else "class.deactivated", target=school_class)
    return school_class


@transaction.atomic
def add_section(request, school_class, name):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, school_class)
    section = save_or_explain(
        Section(school=request.school, school_class=school_class, name=_name(name)),
        "That class already has a section with that name.",
    )
    record(request, "section.created", target=section)
    return section


@transaction.atomic
def assign_class_teacher(request, *, school_class, session, teacher, section=None):
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, school_class, session, teacher, *([section] if section else []))
    existing = (
        ClassTeacher.objects.for_school(request.school)
        .filter(school_class=school_class, session=session, section=section)
        .first()
    )
    if existing:
        if existing.teacher_id == teacher.pk:
            return existing
        previous = existing.teacher.user.get_username()
        existing.teacher = teacher
        save_or_explain(existing, "Could not change the class teacher.")
        record(
            request, "class_teacher.changed", target=existing,
            previous=previous, new=teacher.user.get_username(),
        )
        return existing
    assignment = save_or_explain(
        ClassTeacher(
            school=request.school, school_class=school_class, section=section,
            session=session, teacher=teacher,
        ),
        "This class already has a class teacher for that session.",
    )
    record(request, "class_teacher.assigned", target=assignment, teacher=teacher.user.get_username())
    return assignment
