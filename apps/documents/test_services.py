import pytest
from django.core.exceptions import PermissionDenied
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.audit.models import AuditLog
from apps.schools.models import Membership

from .models import Document
from .services import archive_document, may_view, upload_document

pytestmark = pytest.mark.django_db


def test_owner_upload_saves_and_audits(school_a, make_request):
    request = make_request(school_a, role=Membership.Role.OWNER)
    document = upload_document(
        request,
        title="P.T.A. circular",
        description="Dates for the term",
        file=SimpleUploadedFile("pta.pdf", b"%PDF"),
        audience=Document.Audience.EVERYONE,
        category="Circular",
    )
    saved = Document.objects.get(pk=document.pk)
    assert saved.title == "P.T.A. circular" and saved.school == school_a
    assert saved.audience == "everyone" and saved.is_active is True
    assert AuditLog.objects.filter(action="documents.document_uploaded").exists()


def test_teacher_and_bursar_cannot_upload(school_a, make_request):
    for role in (Membership.Role.TEACHER, Membership.Role.BURSAR):
        request = make_request(school_a, role=role)
        with pytest.raises(PermissionDenied):
            upload_document(
                request,
                title="No entry",
                description="",
                file=SimpleUploadedFile("x.txt", b"y"),
                audience=Document.Audience.MANAGERS,
            )
    assert not Document.objects.exists()


def test_invalid_audience_refused(school_a, make_request):
    request = make_request(school_a, role=Membership.Role.OWNER)
    with pytest.raises(Exception, match="valid audience"):
        upload_document(
            request,
            title="x",
            description="",
            file=SimpleUploadedFile("x.txt", b"y"),
            audience="nobody",
        )
    assert not Document.objects.exists()


def test_archive_keeps_the_row_and_audits(school_a, make_request):
    request = make_request(school_a, role=Membership.Role.OWNER)
    document = upload_document(
        request,
        title="Old form",
        description="",
        file=SimpleUploadedFile("old.pdf", b"%PDF"),
        audience=Document.Audience.MANAGERS,
    )
    archive_document(request, document)
    stored = Document.objects.get(pk=document.pk)
    assert stored.is_active is False
    assert AuditLog.objects.filter(action="documents.document_archived").exists()


def test_foreign_document_cannot_be_archived(school_a, school_b, make_request, make_member):
    manager_b = make_member(school_b, role=Membership.Role.ADMIN)
    foreign = Document.objects.create(
        school=school_b,
        title="B doc",
        file=SimpleUploadedFile("b.pdf", b"%PDF"),
        uploaded_by=manager_b,
    )
    request = make_request(school_a, role=Membership.Role.OWNER)
    with pytest.raises(PermissionDenied):
        archive_document(request, foreign)
    stored = Document.objects.get(pk=foreign.pk)
    assert stored.is_active is True


def test_may_view_follows_the_audience(school_a, make_member):
    document = Document(
        school=school_a,
        title="x",
        file=SimpleUploadedFile("x.pdf", b"y"),
        audience=Document.Audience.MANAGERS,
        uploaded_by=make_member(school_a, role=Membership.Role.OWNER),
    )
    teacher = make_member(school_a, role=Membership.Role.TEACHER)
    manager = make_member(school_a, role=Membership.Role.ADMIN)
    assert not may_view(teacher, document)
    assert may_view(manager, document)
