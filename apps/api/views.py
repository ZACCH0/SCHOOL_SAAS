from decimal import Decimal

from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
from django.db.models import Q
from django.http import Http404
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from apps.accounts.identification import AmbiguousIdentifier, resolve_user
from apps.academics.selectors import current_or_last_period, current_session
from apps.announcements.models import Announcement
from apps.announcements.views import AUDIENCE_ROLE_FILTERS
from apps.portal.selectors import children_for
from apps.portal.views import _invoice_rows
from apps.results.services import published_subject_results
from apps.schools.models import Membership
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES
from apps.students.models import GuardianLink, Student
from apps.timetable.models import TimetableSlot
from apps.timetable.selectors import covering_slots

from .access import api_membership, require_api_role

ANNOUNCEMENT_PAGE_SIZE = 25

GENERIC_LOGIN_ERROR = "Wrong username or password."


@api_view(["POST"])
@permission_classes([AllowAny])
def obtain_token(request):
    """Exchange a username/email/phone + password for an API token.

    Same resolution and lockout as the website login: the identifier is
    resolved to one real user, then the resolved username is
    authenticated so django-axes locks username + IP. Every failure
    looks identical, so probing teaches nothing.
    """
    identifier = str(request.data.get("identifier", "")).strip()
    password = str(request.data.get("password", ""))
    if not identifier or not password:
        return Response(
            {"detail": GENERIC_LOGIN_ERROR}, status=status.HTTP_400_BAD_REQUEST
        )
    try:
        account = resolve_user(identifier)
    except AmbiguousIdentifier:
        account = None
    username = account.username if account is not None else identifier
    # The raw HttpRequest, not DRF's wrapper: axes flags the lockout on the
    # request object it is given, and AxesMiddleware (outside the view) then
    # turns that flag into the 429 lockout response.
    user = authenticate(request._request, username=username, password=password)
    if user is None:
        return Response(
            {"detail": GENERIC_LOGIN_ERROR}, status=status.HTTP_400_BAD_REQUEST
        )
    token, _ = Token.objects.get_or_create(user=user)
    return Response({"token": token.key, "username": user.username})


@api_view(["GET"])
def me(request):
    """Who the token belongs to and where it acts."""
    membership = api_membership(request)
    if membership is None:
        raise PermissionDenied
    session = current_session(membership.school)
    period = current_or_last_period(session) if session else None
    return Response(
        {
            "username": request.user.username,
            "full_name": request.user.get_full_name(),
            "school": membership.school.name,
            "role": membership.role,
            "role_label": membership.get_role_display(),
            "session": session.name if session else None,
            "period": period.name if period else None,
        }
    )


def _classline(pupil):
    if not pupil.current_class_id:
        return "No class yet"
    line = str(pupil.current_class)
    if pupil.current_section_id:
        line += f" - {pupil.current_section}"
    return line


def _owed(school, pupil):
    invoices = _invoice_rows(school, pupil)
    return sum((i.balance_due for i in invoices if i.balance_due > 0), Decimal("0"))


@api_view(["GET"])
def children(request):
    """The parent's linked children with fee balance and published count."""
    membership = require_api_role(request, (Membership.Role.PARENT,))
    session = current_session(membership.school)
    period = current_or_last_period(session) if session else None
    data = []
    for pupil in children_for(membership):
        published = (
            published_subject_results(membership.school, pupil, period).count()
            if period
            else 0
        )
        data.append(
            {
                "id": pupil.pk,
                "first_name": pupil.first_name,
                "last_name": pupil.last_name,
                "class": _classline(pupil),
                "status": pupil.status,
                "owed": str(_owed(membership.school, pupil)),
                "published_results": published,
            }
        )
    return Response({"children": data})


@api_view(["GET"])
def announcements(request):
    """Audience-filtered notices, same rule as the notice board."""
    membership = api_membership(request)
    if membership is None:
        raise PermissionDenied
    role = membership.role
    if role in MANAGE_STRUCTURE_ROLES:
        audience_filter = Q()
    else:
        audience_filter = Q(
            audience__in=[
                value
                for value, roles in AUDIENCE_ROLE_FILTERS.items()
                if role in roles
            ]
        )
    rows = (
        Announcement.objects.for_school(membership.school)
        .filter(is_active=True)
        .filter(audience_filter)
        .select_related("published_by")
        .order_by("-created_at", "-id")[:ANNOUNCEMENT_PAGE_SIZE]
    )
    return Response(
        {
            "announcements": [
                {
                    "id": row.pk,
                    "title": row.title,
                    "body": row.body,
                    "audience": row.audience,
                    "published_by": str(row.published_by),
                    "created_at": row.created_at.isoformat(),
                }
                for row in rows
            ]
        }
    )


@api_view(["GET"])
def my_timetable(request):
    """The teacher's own lessons for the current session, grouped by day."""
    membership = require_api_role(request, (Membership.Role.TEACHER,))
    session = current_session(membership.school)
    if session is None:
        return Response({"session": None, "days": []})
    by_day = {}
    for slot in covering_slots(membership.school, session, membership):
        by_day.setdefault(slot.day, []).append(slot)
    days = [
        {
            "name": TimetableSlot.WeekDay(day).label,
            "slots": [
                {
                    "subject": str(slot.subject),
                    "class": str(slot.school_class),
                    "section": str(slot.section) if slot.section_id else None,
                    "starts_at": slot.starts_at.strftime("%H:%M"),
                    "ends_at": slot.ends_at.strftime("%H:%M"),
                }
                for slot in by_day[day]
            ],
        }
        for day in sorted(by_day)
    ]
    return Response({"session": session.name, "days": days})


@api_view(["GET"])
def child_results(request, pk):
    """One child's published results for the current period."""
    membership = require_api_role(request, (Membership.Role.PARENT,))
    pupil = (
        Student.objects.for_school(membership.school)
        .select_related("current_class", "current_class__level", "current_section")
        .filter(pk=pk)
        .first()
    )
    if pupil is None or not GuardianLink.objects.filter(
        school=membership.school, student=pupil, guardian=membership
    ).exists():
        raise Http404
    session = current_session(membership.school)
    period = current_or_last_period(session) if session else None
    results = (
        list(published_subject_results(membership.school, pupil, period))
        if period
        else []
    )
    average = (
        sum((r.percentage for r in results), Decimal("0")) / len(results)
        if results
        else None
    )
    return Response(
        {
            "student": {
                "id": pupil.pk,
                "first_name": pupil.first_name,
                "last_name": pupil.last_name,
                "class": _classline(pupil),
            },
            "session": session.name if session else None,
            "period": period.name if period else None,
            "average": str(average.quantize(Decimal("0.1"))) if average is not None else None,
            "results": [
                {
                    "subject": str(row.sheet.subject),
                    "total": str(row.total),
                    "percentage": str(row.percentage),
                    "grade": row.grade,
                    "remark": row.grade_remark,
                }
                for row in results
            ],
        }
    )
