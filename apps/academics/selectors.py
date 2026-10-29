from django.utils import timezone

from .models import AcademicSession


def current_session(school):
    """The school's current academic session, or None."""
    return AcademicSession.objects.for_school(school).filter(is_current=True).first()


def session_periods(session):
    """The session's periods (terms), in date order."""
    return list(session.periods.order_by("start_date", "id"))


def current_or_last_period(session):
    """The period whose dates cover today, else the last term of the session."""
    periods = session_periods(session)
    today = timezone.localdate()
    for period in periods:
        if period.start_date <= today <= period.end_date:
            return period
    return periods[-1] if periods else None
