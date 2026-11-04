import os

from django.contrib import messages
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import EmptyPage, PageNotAnInteger, Paginator
from django.db.models import Q
from django.http import FileResponse, Http404
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.decorators.http import require_POST

from apps.schools.lookups import get_for_school_or_404
from apps.schools.models import Membership
from apps.schools.permissions import MANAGE_STRUCTURE_ROLES, membership_required, role_required

from .forms import DocumentForm
from .models import Document
from .services import AUDIENCE_ROLES, archive_document, may_view, upload_document

manager_only = role_required(*MANAGE_STRUCTURE_ROLES)

PAGE_SIZE = 25


def _text(exc):
    return " ".join(exc.messages)


def _visible_audiences(role):
    return [value for value, roles in AUDIENCE_ROLES.items() if role in roles]


@membership_required
def document_list(request):
    """Owners and admins see everything; other roles see their audience's documents."""
    role = request.membership.role
    if role in MANAGE_STRUCTURE_ROLES:
        audience_filter = Q()
    else:
        audience_filter = Q(audience__in=_visible_audiences(role))
    documents = (
        Document.objects.for_school(request.school)
        .filter(is_active=True)
        .filter(audience_filter)
        .select_related("uploaded_by")
        .order_by("-created_at", "-id")
    )
    paginator = Paginator(documents, PAGE_SIZE)
    try:
        page_obj = paginator.page(request.GET.get("page", "1"))
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)
    return render(
        request,
        "documents/list.html",
        {"page_obj": page_obj, "is_manager": role in MANAGE_STRUCTURE_ROLES},
    )


@manager_only
def document_upload(request):
    form = DocumentForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        data = form.cleaned_data
        try:
            document = upload_document(
                request,
                title=data["title"],
                category=data["category"],
                description=data["description"],
                audience=data["audience"],
                file=data["file"],
            )
        except ValidationError as exc:
            form.add_error(None, exc)
        else:
            messages.success(request, f"Document shared: {document.title}.")
            return redirect("documents:list")
    return render(
        request,
        "form_page.html",
        {
            "form": form,
            "title": "Share a document",
            "cancel_url": reverse("documents:list"),
        },
    )


@membership_required
def document_download(request, pk):
    """Access is checked on every download; direct media URLs are never exposed."""
    document = get_for_school_or_404(
        Document.objects.filter(is_active=True), request, pk=pk
    )
    if not may_view(request.membership, document):
        raise PermissionDenied
    if not document.file.storage.exists(document.file.name):
        raise Http404
    return FileResponse(
        document.file.open("rb"),
        as_attachment=False,
        filename=os.path.basename(document.file.name),
    )


@manager_only
@require_POST
def document_archive(request, pk):
    document = get_for_school_or_404(Document, request, pk=pk)
    try:
        archive_document(request, document)
    except ValidationError as exc:
        messages.error(request, _text(exc))
    else:
        messages.success(request, "Document taken down.")
    return redirect("documents:list")
