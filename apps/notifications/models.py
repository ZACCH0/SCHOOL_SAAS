from django.db import models

from apps.schools.models import ValidatedSchoolModel


class Notification(ValidatedSchoolModel):
    """One message in one member's bell: something happened that concerns them.

    A member only ever sees their own; the bell count is per membership.
    """

    recipient = models.ForeignKey(
        "schools.Membership", on_delete=models.PROTECT, related_name="notifications",
    )
    kind = models.CharField(
        max_length=50,
        help_text="What happened, e.g. results.sheet_sent_back.",
    )
    title = models.CharField(max_length=200)
    body = models.TextField(blank=True)
    url = models.CharField(
        max_length=255,
        blank=True,
        help_text="Where the bell links to, e.g. a sheet page.",
    )
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["school", "recipient", "is_read", "created_at"]),
        ]

    def clean(self):
        super().clean()
        self.ensure_same_school("recipient")

    def __str__(self):
        return self.title
