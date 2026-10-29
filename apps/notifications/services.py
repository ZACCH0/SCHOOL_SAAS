"""Rules for who receives which notification. Called inside services, in the
same transaction as the action they report."""
from apps.notifications.models import Notification
from apps.schools.models import Membership


def notify_memberships(request, recipients, *, kind, title, body="", url=""):
    """Create one notification per distinct membership, skipping the actor."""
    actors_school = request.school
    membership = request.membership
    created = []
    seen = set()
    for recipient in recipients:
        if recipient is None or recipient.pk in seen:
            continue
        seen.add(recipient.pk)
        if membership is not None and recipient.pk == membership.pk:
            continue
        if recipient.school_id != actors_school.id:
            continue
        created.append(
            Notification.objects.create(
                school=actors_school,
                recipient=recipient,
                kind=kind,
                title=title,
                body=body or "",
                url=url or "",
            )
        )
    return created


def office_memberships(school):
    """The active owner/admin memberships of a school: the people who
    review, approve and publish result sheets."""
    return list(
        Membership.objects.filter(
            school=school, is_active=True,
            role__in=(Membership.Role.OWNER, Membership.Role.ADMIN),
        )
    )


def unread_count(request):
    """How many of this member's school notifications are still unread."""
    membership = request.membership
    return Notification.objects.for_school(request.school).filter(
        recipient=membership, is_read=False,
    ).count()
