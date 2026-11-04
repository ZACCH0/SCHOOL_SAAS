import pytest
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.schools.models import Membership

from .models import Document

pytestmark = pytest.mark.django_db


def member(school, role=Membership.Role.OWNER):
    from apps.schools.models import Membership as M

    from django.contrib.auth import get_user_model

    user = get_user_model().objects.create_user(f"{role}-doc-user", password="S3cure-pass!")
    return M.objects.create(user=user, school=school, role=role)


def file_row(school, uploader, name="policy.txt", content=b"hello", **kwargs):
    return Document(
        school=school,
        title="Behaviour policy",
        file=SimpleUploadedFile(name, content),
        uploaded_by=uploader,
        **kwargs,
    )


def test_default_audience_is_managers():
    document = Document(title="x", file=SimpleUploadedFile("a.pdf", b"y"))
    assert document.audience == Document.Audience.MANAGERS


def test_tenant_isolation_by_query(school_a, school_b):
    Document.objects.create(
        school=school_b,
        title="Beta handbook",
        file=SimpleUploadedFile("beta.pdf", b"y"),
        uploaded_by=member(school_b),
    )
    assert not Document.objects.for_school(school_a).exists()


def test_foreign_uploaded_by_is_refused(school_a, school_b, make_member):
    foreign = make_member(school_b, role=Membership.Role.OWNER)
    document = file_row(school_a, foreign)
    with pytest.raises(ValidationError, match="different school"):
        document.clean()


def test_non_manager_uploader_is_refused(school_a, make_member):
    teacher = make_member(school_a, role=Membership.Role.TEACHER)
    document = file_row(school_a, teacher)
    with pytest.raises(ValidationError, match="owner or an admin"):
        document.clean()


def test_wrong_extension_is_refused(school_a, make_member):
    manager = make_member(school_a, role=Membership.Role.OWNER)
    document = file_row(school_a, manager, name="notes.exe")
    with pytest.raises(ValidationError, match="Only PDF"):
        document.clean()


def test_oversize_upload_is_refused(school_a, make_member):
    manager = make_member(school_a, role=Membership.Role.OWNER)
    document = file_row(school_a, manager, content=b"x" * (21 * 1024 * 1024))
    with pytest.raises(ValidationError, match="MB"):
        document.clean()


def test_rules_run_on_save_and_path_is_school_scoped(school_a, make_member):
    manager = make_member(school_a, role=Membership.Role.OWNER)
    document = file_row(school_a, manager, name="readme.txt")
    document.save()
    stored = Document.objects.get(pk=document.pk)
    assert stored.file.name.startswith(f"documents/school-{school_a.pk}/")
