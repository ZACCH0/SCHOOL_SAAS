from django.conf import settings
from django.db import models

# Create your models here.

class School(models.Model):
    """A tenant. Every school-owned record points to one School."""

    name = models.CharField(max_length=200)
    slug = models.SlugField(unique=True)
    address = models.TextField(blank=True)
    phone = models.CharField(max_length=20, blank=True)
    email = models.EmailField(blank=True)
    website = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]

    def __str__(self):
        return self.name


class Membership(models.Model):
    """Links a user to a school with one role."""

    class Role(models.TextChoices):
        OWNER = "owner", "School Owner"
        ADMIN = "admin", "School Admin"
        TEACHER = "teacher", "Teacher"
        BURSAR = "bursar", "Bursar/Accountant"
        PARENT = "parent", "Parent/Guardian"
        STUDENT = "student", "Student"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="memberships",
    )
    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name="memberships",
    )
    role = models.CharField(max_length=20, choices=Role.choices)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user", "school", "role"],
                name="unique_user_school_role",
            )
        ]
        indexes = [models.Index(fields=["school", "role"])]

    def __str__(self):
        return f"{self.user} - {self.get_role_display()} at {self.school}"
    
class SchoolQuerySet(models.QuerySet):
    def for_school(self, school):
        """Always use this in views/services. Never fetch school data unscoped."""
        return self.filter(school=school)


class SchoolOwnedModel(models.Model):
    """Base class for every record that belongs to one school."""

    school = models.ForeignKey(
        School,
        on_delete=models.PROTECT,
        related_name="%(app_label)s_%(class)s_set",
    )

    objects = SchoolQuerySet.as_manager()

    class Meta:
        abstract = True    