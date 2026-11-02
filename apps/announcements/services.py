from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import record
from apps.notifications.services import notify_memberships
from apps.schools.models import Membership
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, require_role
from apps.schools.service_helpers import ensure_owned, save_or_explain

from .models import Announcement

AUDIENCE_ROLES = {
    Announcement.Audience.EVERYONE: tuple(Membership.Role.values),
    Announcement.Audience.STAFF: (
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
        Membership.Role.BURSAR,
    ),
    Announcement.Audience.TEACHERS: (Membership.Role.TEACHER,),
    Announcement.Audience.PARENTS: (Membership.Role.PARENT,),
}


def _recipients(school, audience):
    """The active memberships the announcement should reach."""
    roles = AUDIENCE_ROLES[audience]
    return list(
        Membership.objects.filter(school=school, is_active=True, role__in=roles)
    )


@transaction.atomic
def create_announcement(request, *, title, body, audience):
    """The office publishes a notice to a chosen audience."""
    require_role(request, MANAGE_STRUCTURE_ROLES)
    if audience not in Announcement.Audience.values:
        raise ValidationError("Choose a valid audience.")
    announcement = save_or_explain(
        Announcement(
            school=request.school,
            title=(title or "").strip(),
            body=(body or "").strip(),
            audience=audience,
            published_by=request.membership,
        ),
        "Could not save the announcement.",
    )
    notify_memberships(
        request,
        _recipients(request.school, audience),
        kind="announcements.published",
        title=f"New announcement: {announcement.title}",
        body=announcement.body,
        url="/announcements/",
    )
    record(
        request,
        "announcements.announcement_created",
        target=announcement,
        audience=audience,
    )
    return announcement


@transaction.atomic
def archive_announcement(request, announcement):
    """Take a notice down without deleting it."""
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, announcement)
    announcement.is_active = False
    save_or_explain(announcement, "Could not save the announcement.")
    record(
        request, "announcements.announcement_archived", target=announcement,
    )
    return announcement
