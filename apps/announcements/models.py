from django.core.exceptions import ValidationError
from django.db import models

from apps.schools.models import Membership, ValidatedSchoolModel


class Announcement(ValidatedSchoolModel):
    """A notice the office publishes to a chosen audience inside one school."""

    class Audience(models.TextChoices):
        EVERYONE = "everyone", "Everyone"
        STAFF = "staff", "Staff (owner, admin, bursar)"
        TEACHERS = "teachers", "Teachers"
        PARENTS = "parents", "Parents"

    title = models.CharField(max_length=200)
    body = models.TextField()
    audience = models.CharField(
        max_length=10, choices=Audience.choices, default=Audience.EVERYONE
    )
    published_by = models.ForeignKey(
        Membership, on_delete=models.PROTECT, related_name="announcements"
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
        self.ensure_same_school("published_by")
        if (
            self.published_by_id
            and self.published_by.role
            not in (Membership.Role.OWNER, Membership.Role.ADMIN)
        ):
            raise ValidationError(
                "Only the owner or an admin can publish an announcement."
            )

    def __str__(self):
        return self.title
