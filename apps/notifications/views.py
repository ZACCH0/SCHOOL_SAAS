from django import forms
from django.shortcuts import redirect, render
from django.views.decorators.http import require_POST

from apps.schools.permissions import membership_required

from .models import Notification
from .services import unread_count


@membership_required
def list_notifications(request):
    return render(
        request, "notifications/list.html",
        {
            "notifications": Notification.objects.for_school(request.school)
            .filter(recipient=request.membership)
            .select_related("recipient__user")[:50],
            "unread": unread_count(request),
        },
    )


@require_POST
@membership_required
def mark_read(request, pk):
    unread = (
        Notification.objects.for_school(request.school)
        .filter(recipient=request.membership, is_read=False, pk=pk)
        .first()
    )
    if unread:
        unread.is_read = True
        unread.save(update_fields=["is_read"])
    return redirect("notifications:list")


@require_POST
@membership_required
def mark_all_read(request):
    Notification.objects.for_school(request.school).filter(
        recipient=request.membership, is_read=False
    ).update(is_read=True)
    return redirect("notifications:list")
