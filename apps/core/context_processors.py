from apps.academics.models import AcademicPeriod
from .navigation import bottom_bar_for, nav_for

def shell(request):
    membership = getattr(request, "membership", None)
    if membership is None:
        return {}
    period = (
        AcademicPeriod.objects.for_school(request.school)
        .filter(is_current=True)
        .select_related("session")
        .first()
    )
    bar = bottom_bar_for(request, membership)
    return {
        "nav_items": nav_for(request, membership),
        "nav_favourites": bar["items"],
        "nav_more": bar["more"],
        "current_period": period,
    }


def unread_notifications(request):
    """A lightweight read for the bell in the top bar."""
    if getattr(request, "membership", None) is None:
        return {}
    from apps.notifications.services import unread_count
    return {"unread_notifications": unread_count(request)}