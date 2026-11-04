import uuid

from django.core.exceptions import ValidationError
from django.db import models

from apps.schools.models import Membership, ValidatedSchoolModel

MAX_DOCUMENT_SIZE = 20

ALLOWED_EXTENSIONS = (
    ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".png", ".jpg", ".jpeg", ".txt",
)


def document_upload_path(instance, filename):
    return f"documents/school-{instance.school_id}/{uuid.uuid4().hex}_{filename}"


class Document(ValidatedSchoolModel):
    """A file the office shares with a chosen audience inside one school."""

    class Audience(models.TextChoices):
        MANAGERS = "managers", "Managers only"
        STAFF = "staff", "All staff"
        EVERYONE = "everyone", "Everyone (incl. parents)"

    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100, blank=True)
    description = models.TextField(blank=True)
    file = models.FileField(upload_to=document_upload_path)
    audience = models.CharField(
        max_length=10, choices=Audience.choices, default=Audience.MANAGERS
    )
    uploaded_by = models.ForeignKey(
        Membership, on_delete=models.PROTECT, related_name="documents"
    )
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["school", "audience", "is_active"]),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("uploaded_by")
        if (
            self.uploaded_by_id
            and self.uploaded_by.role
            not in (Membership.Role.OWNER, Membership.Role.ADMIN)
        ):
            raise ValidationError(
                "Only the owner or an admin can upload a document."
            )
        if self.file:
            name = self.file.name
            extension = name.rsplit(".", 1)[-1].lower() if "." in name else ""
            if f".{extension}" not in ALLOWED_EXTENSIONS:
                raise ValidationError(
                    "Only PDF, Word, Excel, image or text documents are allowed."
                )
            if not getattr(self.file, "_committed", True):
                if self.file.size > MAX_DOCUMENT_SIZE * 1024 * 1024:
                    raise ValidationError(
                        f"Choose a file up to {MAX_DOCUMENT_SIZE} MB."
                    )

    def __str__(self):
        return self.title
