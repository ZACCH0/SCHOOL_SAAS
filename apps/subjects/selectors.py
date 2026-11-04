"""Read-only helpers for teacher assignments."""

from .models import TeacherAssignment


def assignments_for(school, membership, session):
    """This membership's teaching assignments for one session, fully loaded."""
    return list(
        TeacherAssignment.objects.filter(
            school=school, session=session, teacher=membership,
        )
        .select_related("school_class", "school_class__level", "section", "subject")
    )


def assignment_covers(assignments, *, school_class_id, subject_id,
                      section_id=None):
    """True when any of these assignments covers the given spot.

    A class-wide assignment (section=None) covers every section of the
    class; an exact-section assignment covers only its own section. This is
    the ONE coverage rule shared by score entry eligibility, the teacher's
    timetable, and the teacher dashboard."""
    return any(
        a.school_class_id == school_class_id
        and (subject_id is None or a.subject_id == subject_id)
        and (a.section_id is None or a.section_id == section_id)
        for a in assignments
    )
