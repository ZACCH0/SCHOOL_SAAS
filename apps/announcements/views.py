from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.schools.lookups import get_for_school_or_404
from apps.schools.models import Membership
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, membership_required, role_required

from .forms import AnnouncementForm
from .models import Announcement
from .services import archive_announcement, create_announcement

manager_only = role_required(*MANAGE_STRUCTURE_ROLES)

PAGE_SIZE = 25

# Wording of the audience rule: managers see every notice; other roles see
# a notice when their role is included in its audience.
AUDIENCE_ROLE_FILTERS = {
    Announcement.Audience.EVERYONE: tuple(Membership.Role.values),
    Announcement.Audience.STAFF: (Membership.Role.OWNER, Membership.Role.ADMIN, Membership.Role.BURSAR),
    Announcement.Audience.TEACHERS: (Membership.Role.TEACHER,),
    Announcement.Audience.PARENTS: (Membership.Role.PARENT,),
}


def _text(exc):
    return " ".join(exc.messages)


@membership_required
def announcement_list(request):
    """The notice board. Managers see everything; other roles only the
    notices addressed to their role."""
    role = request.membership.role
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
    announcements = (
        Announcement.objects.for_school(request.school)
        .filter(is_active=True)
        .filter(audience_filter)
        .select_related("published_by")
        .order_by("-created_at", "-id")
    )
    paginator = Paginator(announcements, PAGE_SIZE)
    try:
        page_obj = paginator.page(request.GET.get("page", "1"))
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    return render(
        request, "announcements/list.html",
        {
            "page_obj": page_obj,
            "is_manager": role in MANAGE_STRUCTURE_ROLES,
        },
    )


@manager_only
def announcement_create(request):
    form = AnnouncementForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            announcement = create_announcement(
                request,
                title=data["title"],
                body=data["body"],
                audience=data["audience"],
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"Announcement published: {announcement.title}.")
            return redirect("announcements:list")
    return render(
        request, "form_page.html",
        {
            "form": form,
            "title": "New announcement",
            "cancel_url": reverse("announcements:list"),
        },
    )


@manager_only
@require_POST
def announcement_archive(request, pk):
    announcement = get_for_school_or_404(Announcement, request, pk=pk)
    try:
        archive_announcement(request, announcement)
    except ValidationError as exc:
        messages.error(request, _text(exc))
    else:
        messages.success(request, "Announcement taken down.")
    return redirect("announcements:list")
