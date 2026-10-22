from django.db import transaction
from .models import Level, SchoolClass

STANDARD_STRUCTURE = [
    ("Primary", True, ["Primary 1", "Primary 2", "Primary 3", "Primary 4", "Primary 5", "Primary 6"]),
    ("Junior Secondary", False, ["JSS 1", "JSS 2", "JSS 3"]),
    ("Senior Secondary", False, ["SS 1", "SS 2", "SS 3"]),
]


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