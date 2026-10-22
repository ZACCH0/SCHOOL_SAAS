from django.conf import settings
from django.db import models

class AuditLogImmutable(Exception):
    """Raised when someone tries to change or delete an audit entry."""

class AuditLogQuerySet(models.QuerySet):
    def for_school(self, school):
        return self.filter(school=school)

    def update(self, **kwargs):
        raise AuditLogImmutable("Audit entries cannot be changed.")

    def delete(self):
        raise AuditLogImmutable("Audit entries cannot be deleted.")

class AuditLog(models.Model):
    """One thing that happened. Append only."""
    school = models.ForeignKey(
        "schools.School",
        null=True,
        blank=True,
        on_delete=models.PROTECT,
        related_name="audit_entries",
    )
    actor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="audit_entries",
    )
    actor_label = models.CharField(max_length=150, blank=True)
    action = models.CharField(max_length=80, db_index=True)
    target_type = models.CharField(max_length=100, blank=True)
    target_id = models.CharField(max_length=64, blank=True)
    target_repr = models.CharField(max_length=200, blank=True)
    metadata = models.JSONField(default=dict, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    objects = AuditLogQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [
            models.Index(fields=["school", "-created_at"]),
            models.Index(fields=["target_type", "target_id"]),
        ]

    def save(self, *args, **kwargs):
        if not self._state.adding:
            raise AuditLogImmutable("Audit entries cannot be changed.")
        super().save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        raise AuditLogImmutable("Audit entries cannot be deleted.")

    def __str__(self):
        return f"{self.created_at:%Y-%m-%d %H:%M} {self.actor_label or 'system'} {self.action}"