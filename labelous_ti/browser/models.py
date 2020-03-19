from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager

# ripped off of django's
class UserManager(BaseUserManager):
    def _create_user(self, email, password, **extra_fields):
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', False)
        extra_fields.setdefault('is_superuser', False)

        return self._create_user(email, password, **extra_fields)

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self._create_user(email, password, **extra_fields)


class User(AbstractUser):
    USERNAME_FIELD = 'email'
    username = None # we don't have usernames any more
    email = models.EmailField(unique=True)
    REQUIRED_FIELDS = []

    password_reset_token = models.BinaryField(max_length=16, null=True)

    objects = UserManager()

    # not exactly the correct place maybe but eh
    class Meta:
        permissions = [
            ("reviewer", "Can review others' annotations."),
            ("account_manager", "Can create accounts and reset passwords."),
        ]
