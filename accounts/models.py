from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from django.db import models
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

from .managers import UserManager


class User(AbstractBaseUser, PermissionsMixin):
    """Custom user model for Matritwa with role-based access."""

    class Role(models.TextChoices):
        PATIENT = "patient", _("Patient / Pregnant Woman")
        DOCTOR = "doctor", _("Doctor")
        FCHV = "fchv", _("FCHV Worker")
        ADMIN = "admin", _("Admin")

    email = models.EmailField(_("email address"), unique=True)
    phone = models.CharField(_("phone number"), max_length=20, blank=True)
    first_name = models.CharField(_("first name"), max_length=150, blank=True)
    last_name = models.CharField(_("last name"), max_length=150, blank=True)
    role = models.CharField(
        _("role"),
        max_length=20,
        choices=Role.choices,
        default=Role.PATIENT,
    )

    is_staff = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    is_onboarded = models.BooleanField(
        default=False,
        help_text=_("Marks if the user has completed the onboarding flow."),
    )

    date_joined = models.DateTimeField(default=timezone.now)

    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = ["first_name", "last_name"]

    objects = UserManager()

    class Meta:
        verbose_name = _("user")
        verbose_name_plural = _("users")
        ordering = ["-date_joined"]

    def __str__(self):
        return f"{self.get_full_name()} <{self.email}> [{self.role}]"

    def get_full_name(self):
        return f"{self.first_name} {self.last_name}".strip()

    def get_short_name(self):
        return self.first_name

    @property
    def is_patient(self):
        return self.role == self.Role.PATIENT

    @property
    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    @property
    def is_fchv(self):
        return self.role == self.Role.FCHV


class PatientProfile(models.Model):
    """Extended profile for patients (pregnant women)."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="patient_profile"
    )

    date_of_birth = models.DateField(null=True, blank=True)
    blood_group = models.CharField(max_length=10, blank=True)
    address = models.TextField(blank=True)
    district = models.CharField(max_length=100, blank=True)
    province = models.CharField(max_length=100, blank=True)

    # Pregnancy info
    last_menstrual_period = models.DateField(
        null=True, blank=True, verbose_name="LMP (Last Menstrual Period)"
    )
    expected_delivery_date = models.DateField(null=True, blank=True)
    gravida = models.PositiveSmallIntegerField(
        default=1, help_text="Number of pregnancies"
    )
    parity = models.PositiveSmallIntegerField(
        default=0, help_text="Number of live births"
    )

    profile_picture = models.ImageField(
        upload_to="profiles/patients/", null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Patient Profile"
        verbose_name_plural = "Patient Profiles"

    def __str__(self):
        return f"Patient: {self.user.get_full_name()}"


class DoctorProfile(models.Model):
    """Extended profile for doctors."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="doctor_profile"
    )

    specialization = models.CharField(max_length=200, blank=True)
    license_number = models.CharField(max_length=100, blank=True)
    hospital_name = models.CharField(max_length=200, blank=True)
    years_of_experience = models.PositiveSmallIntegerField(default=0)
    available_for_consultation = models.BooleanField(default=True)

    profile_picture = models.ImageField(
        upload_to="profiles/doctors/", null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Doctor Profile"
        verbose_name_plural = "Doctor Profiles"

    def __str__(self):
        return f"Dr. {self.user.get_full_name()} — {self.specialization}"


class FCHVProfile(models.Model):
    """Extended profile for Female Community Health Volunteers."""

    user = models.OneToOneField(
        User, on_delete=models.CASCADE, related_name="fchv_profile"
    )

    ward_number = models.CharField(max_length=20, blank=True)
    municipality = models.CharField(max_length=100, blank=True)
    district = models.CharField(max_length=100, blank=True)
    years_active = models.PositiveSmallIntegerField(default=0)

    profile_picture = models.ImageField(
        upload_to="profiles/fchv/", null=True, blank=True
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "FCHV Profile"
        verbose_name_plural = "FCHV Profiles"

    def __str__(self):
        return f"FCHV: {self.user.get_full_name()} — {self.municipality}"
