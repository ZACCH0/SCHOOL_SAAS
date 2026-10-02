
from django.contrib.auth.models import AbstractUser
from django.db import models
# Create your models here.

class User(AbstractUser):
    """Platform user. Username login; email and phone are optional."""

    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.get_full_name() or self.username