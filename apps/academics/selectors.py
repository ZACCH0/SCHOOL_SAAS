from .models import AcademicSession


def current_session(school):
    """The school's current academic session, or None."""
    return AcademicSession.objects.for_school(school).filter(is_current=True).first()
