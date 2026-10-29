from apps.students.models import Student


def children_for(membership):
    """The students this parent membership is linked to, one school only."""
    return list(
        Student.objects.filter(
            guardian_links__guardian=membership,
            guardian_links__school=membership.school,
        )
        .select_related("current_class", "current_class__level", "current_section")
        .order_by("last_name", "first_name")
    )
