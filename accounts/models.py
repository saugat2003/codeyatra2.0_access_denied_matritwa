from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user model with role-based access for Matritwa."""

    class Role(models.TextChoices):
        MOTHER = "mother", "Mother"
        HEALTHCARE_WORKER = "healthcare_worker", "Healthcare Worker"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.MOTHER,
    )
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_mother(self):
        return self.role == self.Role.MOTHER

    @property
    def is_healthcare_worker(self):
        return self.role == self.Role.HEALTHCARE_WORKER


class MotherProfile(models.Model):
    """
    Extended profile for mothers, populated during multi-step registration.
    Step 1: basic details | Step 2: pregnancy info | Step 3: location
    """

    BLOOD_GROUP_CHOICES = [
        ("A+", "A+"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B-", "B-"),
        ("O+", "O+"),
        ("O-", "O-"),
        ("AB+", "AB+"),
        ("AB-", "AB-"),
    ]

    TRACKING_METHOD_CHOICES = [
        ("lmp", "LMP Date"),
        ("week", "Pregnancy Week"),
    ]

    user = models.OneToOneField(
        "accounts.User",
        on_delete=models.CASCADE,
        related_name="mother_profile",
    )

    # ── Step 1: Basic Details ──────────────────────────────────────
    full_name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(null=True, blank=True)
    ward = models.CharField(max_length=100, blank=True)

    # ── Step 2: Pregnancy Details ──────────────────────────────────
    tracking_method = models.CharField(
        max_length=10,
        choices=TRACKING_METHOD_CHOICES,
        default="lmp",
    )
    lmp_date = models.DateField(
        null=True,
        blank=True,
        verbose_name="Last Menstrual Period",
    )
    pregnancy_week = models.PositiveIntegerField(null=True, blank=True)
    is_first_pregnancy = models.BooleanField(default=True)
    has_previous_complications = models.BooleanField(default=False)
    blood_group = models.CharField(
        max_length=5,
        choices=BLOOD_GROUP_CHOICES,
        blank=True,
    )

    # ── Step 3: Location ───────────────────────────────────────────
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True
    )
    address = models.TextField(blank=True)

    # ── Meta ───────────────────────────────────────────────────────
    registration_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mother Profile"
        verbose_name_plural = "Mother Profiles"

    def __str__(self):
        return self.full_name or self.user.username
