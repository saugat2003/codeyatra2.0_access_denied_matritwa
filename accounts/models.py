from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    """Custom user – only healthcare workers & admins log in."""

    class Role(models.TextChoices):
        HEALTHCARE_WORKER = "healthcare_worker", "Healthcare Worker"
        ADMIN = "admin", "Admin"

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.HEALTHCARE_WORKER,
    )
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.get_full_name() or self.username} ({self.get_role_display()})"

    @property
    def is_healthcare_worker(self):
        return self.role == self.Role.HEALTHCARE_WORKER


class MotherProfile(models.Model):
    """
    Pregnant woman record – registered and tracked by FCHV.
    Mothers are NOT system users; they are data records.
    """

    BLOOD_GROUP_CHOICES = [
        ("A+", "A+"), ("A-", "A-"),
        ("B+", "B+"), ("B-", "B-"),
        ("O+", "O+"), ("O-", "O-"),
        ("AB+", "AB+"), ("AB-", "AB-"),
    ]

    # ── Identity ───────────────────────────────────────────────────
    full_name = models.CharField(max_length=255)
    age = models.PositiveIntegerField(null=True, blank=True)
    phone = models.CharField(max_length=20, blank=True, help_text="Optional")

    # ── Pregnancy Details ──────────────────────────────────────────
    pregnancy_week = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Gestational week at time of registration",
    )
    lmp_date = models.DateField(
        null=True, blank=True,
        verbose_name="Last Menstrual Period",
    )
    is_first_pregnancy = models.BooleanField(default=True)
    has_previous_complications = models.BooleanField(default=False)
    blood_group = models.CharField(
        max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True,
    )
    medical_notes = models.TextField(
        blank=True,
        help_text="Basic medical history / pre-existing conditions",
    )

    # ── Location (auto-captured via GPS) ───────────────────────────
    latitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
    )
    longitude = models.DecimalField(
        max_digits=9, decimal_places=6, null=True, blank=True,
    )
    address = models.TextField(blank=True)
    ward = models.CharField(max_length=100, blank=True)

    # ── Registration meta ──────────────────────────────────────────
    registered_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="registered_mothers",
        help_text="FCHV who registered this mother",
    )
    registration_completed = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Mother Profile"
        verbose_name_plural = "Mother Profiles"
        ordering = ["-created_at"]

    def __str__(self):
        return self.full_name or "Unknown Mother"
