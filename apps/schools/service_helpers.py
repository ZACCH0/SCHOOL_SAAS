from django.core.exceptions import PermissionDenied, ValidationError
from django.db import IntegrityError, transaction


def ensure_owned(request, *objects):
    """Refuse any record that belongs to another school than the active one."""
    school = getattr(request, "school", None)
    if school is None:
        raise PermissionDenied
    for obj in objects:
        if obj.school_id != school.pk:
            raise PermissionDenied


def save_or_explain(instance, message):
    """Save a record, turning a database uniqueness error into a friendly message."""
    try:
        with transaction.atomic():
            instance.save()
    except IntegrityError as exc:
        raise ValidationError(message) from exc
    return instance
