import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.urls import reverse

from apps.audit.models import AuditLog
from apps.schools.models import Membership

from .models import Document

pytestmark = pytest.mark.django_db


def make_doc(school, uploader, audience=Document.Audience.MANAGERS, is_active=True):
    return Document.objects.create(
        school=school,
        title=f"Doc {audience} {school.slug}",
        file=SimpleUploadedFile("handbook.pdf", b"%PDF-fake"),
        audience=audience,
        uploaded_by=uploader,
        is_active=is_active,
    )


def test_anonymous_is_sent_to_login(client):
    response = client.get(reverse("documents:list"))
    assert response.status_code == 302 and "login" in response.url


def test_role_matrix_on_the_list(client, school_a, school_b, login_as, make_member):
    owner_b = make_member(school_b, role=Membership.Role.OWNER)
    make_doc(school_b, owner_b, audience=Document.Audience.EVERYONE)
    owner = login_as(school_a, Membership.Role.OWNER)
    make_doc(school_a, owner, audience=Document.Audience.MANAGERS)
    make_doc(school_a, owner, audience=Document.Audience.EVERYONE)
    make_doc(school_a, owner, audience=Document.Audience.STAFF)

    response = client.get(reverse("documents:list"))
    titles = {document.title for document in response.context["page_obj"].object_list}
    assert titles == {"Doc managers alpha", "Doc everyone alpha", "Doc staff alpha"}

    client.post("/accounts/logout/")
    login_as(school_a, Membership.Role.TEACHER)
    titles = {
        document.title for document in
        client.get(reverse("documents:list")).context["page_obj"].object_list
    }
    assert titles == {"Doc everyone alpha", "Doc staff alpha"}

    client.post("/accounts/logout/")
    login_as(school_a, Membership.Role.BURSAR)
    titles = {
        document.title for document in
        client.get(reverse("documents:list")).context["page_obj"].object_list
    }
    assert titles == {"Doc everyone alpha", "Doc staff alpha"}

    client.post("/accounts/logout/")
    login_as(school_a, Membership.Role.PARENT)
    titles = {
        document.title for document in
        client.get(reverse("documents:list")).context["page_obj"].object_list
    }
    assert titles == {"Doc everyone alpha"}


def test_upload_posts_and_audits(client, school_a, login_as):
    login_as(school_a, Membership.Role.OWNER)
    response = client.post(
        reverse("documents:create"),
        {
            "title": "Mid-term circular",
            "category": "Circular",
            "description": "Important",
            "audience": Document.Audience.EVERYONE,
            "file": SimpleUploadedFile("notice.pdf", b"%PDF-fake"),
        },
    )
    assert response.status_code == 302
    document = Document.objects.get(title="Mid-term circular")
    assert document.school == school_a and document.audience == "everyone"
    assert AuditLog.objects.filter(action="documents.document_uploaded").exists()


def test_non_managers_cannot_upload_or_archive(client, school_a, login_as, make_member):
    owner = make_member(school_a, role=Membership.Role.OWNER)
    document = make_doc(school_a, owner)
    login_as(school_a, Membership.Role.TEACHER)
    upload_attempt = client.post(
        reverse("documents:create"),
        {"title": "x", "audience": "everyone"},
    )
    assert upload_attempt.status_code == 403
    archive_attempt = client.post(reverse("documents:archive", args=[document.pk]))
    assert archive_attempt.status_code == 403
    assert Document.objects.filter(pk=document.pk, is_active=True).exists()


def test_archive_hides_but_keeps(client, school_a, login_as):
    owner = login_as(school_a, Membership.Role.OWNER)
    document = make_doc(school_a, owner)
    response = client.post(reverse("documents:archive", args=[document.pk]))
    assert response.status_code == 302
    stored = Document.objects.get(pk=document.pk)
    assert stored.is_active is False
    titles = {
        document.title for document in
        client.get(reverse("documents:list")).context["page_obj"].object_list
    }
    assert document.title not in titles


def test_download_serves_the_file_and_respects_the_audience(client, school_a, login_as, make_member):
    owner = make_member(school_a, role=Membership.Role.OWNER)
    everyone = make_doc(school_a, owner, audience=Document.Audience.EVERYONE)
    managers_only = make_doc(school_a, owner, audience=Document.Audience.MANAGERS)
    login_as(school_a, Membership.Role.PARENT)
    allowed = client.get(reverse("documents:download", args=[everyone.pk]))
    assert allowed.status_code == 200
    assert b"".join(allowed.streaming_content) == b"%PDF-fake"
    forbidden = client.get(reverse("documents:download", args=[managers_only.pk]))
    assert forbidden.status_code == 403


def test_archived_document_returns_404_on_download(client, school_a, login_as, make_member):
    owner = make_member(school_a, role=Membership.Role.OWNER)
    document = make_doc(school_a, owner, is_active=False)
    login_as(school_a, Membership.Role.OWNER)
    assert client.get(reverse("documents:download", args=[document.pk])).status_code == 404


def test_tenant_isolation_by_id(client, school_a, school_b, login_as, make_member):
    owner_b = make_member(school_b, role=Membership.Role.OWNER)
    foreign = make_doc(school_b, owner_b)
    login_as(school_a, Membership.Role.OWNER)
    assert client.get(reverse("documents:download", args=[foreign.pk])).status_code == 404
    assert client.post(reverse("documents:archive", args=[foreign.pk])).status_code == 404
    titles = {
        document.title for document in
        client.get(reverse("documents:list")).context["page_obj"].object_list
    }
    assert not any("beta" in title for title in titles)
