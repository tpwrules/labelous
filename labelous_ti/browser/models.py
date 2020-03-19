from django.db import models
from django.contrib.auth.models import AbstractUser

# Create your models here.

class User(AbstractUser):
    USERNAME_FIELD = 'email'
    email = models.EmailField(unique=True)
    REQUIRED_FIELDS = []

    # not exactly the correct place maybe but eh
    class Meta:
        permissions = [
            ("reviewer", "Can review others' annotations."),
            ("account_manager", "Can create accounts and reset passwords."),
        ]
