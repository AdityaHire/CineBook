from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UserManager(BaseUserManager):
    """Manager that uses email (not username) as the login field."""

    def create_user(self, email, name, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        email = self.normalize_email(email)
        extra_fields.setdefault("role", "user")
        extra_fields.setdefault("is_active", True)
        user = self.model(email=email, name=name, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, name, password=None, **extra_fields):
        extra_fields["role"] = "admin"
        extra_fields["is_staff"] = True
        extra_fields["is_superuser"] = True
        return self.create_user(email, name, password, **extra_fields)


class User(AbstractUser):
    ROLE_USER = "user"
    ROLE_ADMIN = "admin"
    ROLE_CHOICES = [(ROLE_USER, "User"), (ROLE_ADMIN, "Admin")]

    # Remove username; use email as login
    username = None
    email = models.EmailField(unique=True, max_length=254)
    name = models.CharField(max_length=100)
    role = models.CharField(max_length=10, choices=ROLE_CHOICES, default=ROLE_USER)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["name"]

    objects = UserManager()

    class Meta:
        db_table = "users"
        verbose_name = "User"
        verbose_name_plural = "Users"

    def __str__(self):
        return f"{self.name} <{self.email}>"

    @property
    def is_admin(self):
        return self.role == self.ROLE_ADMIN
