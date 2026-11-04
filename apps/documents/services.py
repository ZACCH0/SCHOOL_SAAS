from django.core.exceptions import ValidationError
from django.db import transaction

from apps.audit.services import record
from apps.schools.models import Membership
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, require_role
from apps.schools.service_helpers import ensure_owned, save_or_explain

from .models import Document

AUDIENCE_ROLES = {
    Document.Audience.MANAGERS: (Membership.Role.OWNER, Membership.Role.ADMIN),
    Document.Audience.STAFF: (
        Membership.Role.OWNER,
        Membership.Role.ADMIN,
        Membership.Role.TEACHER,
        Membership.Role.BURSAR,
    ),
    Document.Audience.EVERYONE: tuple(Membership.Role.values),
}


def may_view(member, document):
    """True when the membership's role is covered by the document's audience."""
    roles = AUDIENCE_ROLES[document.audience]
    return member.role in roles


@transaction.atomic
def upload_document(request, *, title, description, file, audience, category=""):
    """The office shares one document with a chosen audience."""
    require_role(request, MANAGE_STRUCTURE_ROLES)
    if audience not in Document.Audience.values:
        raise ValidationError("Choose a valid audience.")
    document = save_or_explain(
        Document(
            school=request.school,
            title=(title or "").strip(),
            category=(category or "").strip(),
            description=(description or "").strip(),
            file=file,
            audience=audience,
            uploaded_by=request.membership,
        ),
        "Could not save the document.",
    )
    record(
        request,
        "documents.document_uploaded",
        target=document,
        audience=audience,
    )
    return document


@transaction.atomic
def archive_document(request, document):
    """Take a document down without deleting the row or the file."""
    require_role(request, MANAGE_STRUCTURE_ROLES)
    ensure_owned(request, document)
    document.is_active = False
    save_or_explain(document, "Could not save the document.")
    record(request, "documents.document_archived", target=document)
    return document
