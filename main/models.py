from django.conf import settings
from django.db import models
from django.utils import timezone


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


# ─── Pregnancy Timeline ──────────────────────────────────────────────────────

class PregnancyMilestone(models.Model):
    """Standard pregnancy milestones — seeded once, shared across all patients."""

    week_number = models.PositiveSmallIntegerField(unique=True)
    title = models.CharField(max_length=200)
    description = models.TextField(help_text="What's happening this week.")
    baby_size = models.CharField(
        max_length=100, blank=True, help_text="e.g. 'Size of a mango'"
    )
    tips = models.TextField(blank=True, help_text="Health tips for this week.")
    trimester = models.PositiveSmallIntegerField(
        choices=[(1, "First"), (2, "Second"), (3, "Third")],
    )

    class Meta:
        ordering = ["week_number"]
        verbose_name = "Pregnancy Milestone"

    def __str__(self):
        return f"Week {self.week_number}: {self.title}"


# ─── Health Streak Tracker ────────────────────────────────────────────────────

class HealthStreak(TimeStampedModel):
    """Daily health-habit log for a patient."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="health_streaks",
    )
    date = models.DateField(default=timezone.now)
    took_vitamins = models.BooleanField(default=False)
    exercised = models.BooleanField(default=False)
    drank_water = models.BooleanField(default=False)
    ate_balanced_meal = models.BooleanField(default=False)
    slept_well = models.BooleanField(default=False)
    notes = models.TextField(blank=True)

    class Meta(TimeStampedModel.Meta):
        unique_together = ("user", "date")
        verbose_name = "Health Streak"

    def __str__(self):
        return f"{self.user.get_short_name()} — {self.date}"

    @property
    def score(self):
        """Number of habits completed out of 5."""
        return sum([
            self.took_vitamins,
            self.exercised,
            self.drank_water,
            self.ate_balanced_meal,
            self.slept_well,
        ])


# ─── Symptom Checker ─────────────────────────────────────────────────────────

class SymptomLog(TimeStampedModel):
    """Patient-reported symptom with severity."""

    SEVERITY_CHOICES = [
        (1, "Mild"),
        (2, "Moderate"),
        (3, "Noticeable"),
        (4, "Severe"),
        (5, "Very Severe"),
    ]

    SYMPTOM_CHOICES = [
        ("nausea", "Nausea / Morning sickness"),
        ("headache", "Headache"),
        ("fatigue", "Fatigue / Tiredness"),
        ("back_pain", "Back pain"),
        ("swelling", "Swelling (feet/hands/face)"),
        ("dizziness", "Dizziness"),
        ("heartburn", "Heartburn / Acidity"),
        ("cramps", "Abdominal cramps"),
        ("bleeding", "Vaginal bleeding"),
        ("reduced_movement", "Reduced fetal movement"),
        ("high_bp", "High blood pressure symptoms"),
        ("fever", "Fever"),
        ("vision_changes", "Blurred vision / Seeing spots"),
        ("shortness_breath", "Shortness of breath"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="symptom_logs",
    )
    symptom = models.CharField(max_length=50, choices=SYMPTOM_CHOICES)
    severity = models.PositiveSmallIntegerField(choices=SEVERITY_CHOICES, default=1)
    description = models.TextField(blank=True, help_text="Describe the symptom.")
    date = models.DateField(default=timezone.now)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Symptom Log"

    def __str__(self):
        return f"{self.get_symptom_display()} ({self.get_severity_display()}) — {self.user.get_short_name()}"

    @property
    def is_danger(self):
        """Returns True if this symptom+severity indicates a danger sign."""
        danger_symptoms = {"bleeding", "vision_changes", "reduced_movement", "high_bp"}
        return self.symptom in danger_symptoms or self.severity >= 4


# ─── Danger Sign Reports ─────────────────────────────────────────────────────

class DangerSignReport(TimeStampedModel):
    """Urgent danger sign reported by the patient."""

    DANGER_SIGN_CHOICES = [
        ("heavy_bleeding", "Heavy vaginal bleeding"),
        ("severe_headache", "Severe, persistent headache"),
        ("blurred_vision", "Blurred vision / Seeing spots"),
        ("high_fever", "High fever (>38°C / 100.4°F)"),
        ("severe_abdominal_pain", "Severe abdominal pain"),
        ("convulsions", "Convulsions / Fits"),
        ("reduced_fetal_movement", "No / Reduced fetal movement"),
        ("water_break", "Water breaking before term"),
        ("severe_swelling", "Severe swelling of face/hands"),
        ("difficulty_breathing", "Difficulty breathing"),
        ("other", "Other"),
    ]

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("reviewed", "Reviewed by FCHV"),
        ("escalated", "Escalated to Doctor"),
        ("resolved", "Resolved"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="danger_sign_reports",
    )
    danger_sign = models.CharField(max_length=50, choices=DANGER_SIGN_CHOICES)
    description = models.TextField(blank=True, help_text="More details about the sign.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reviewed_danger_signs",
    )

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Danger Sign Report"

    def __str__(self):
        return f"{self.get_danger_sign_display()} — {self.user.get_short_name()} [{self.status}]"


# ─── Reminders ────────────────────────────────────────────────────────────────

class Reminder(TimeStampedModel):
    """Reminders for ANC visits, medications, vaccinations, custom."""

    TYPE_CHOICES = [
        ("anc_visit", "ANC Visit"),
        ("medication", "Medication / Supplement"),
        ("vaccination", "Vaccination"),
        ("checkup", "Doctor Check-up"),
        ("custom", "Custom"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="reminders",
    )
    reminder_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    title = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    due_date = models.DateField()
    is_completed = models.BooleanField(default=False)

    class Meta(TimeStampedModel.Meta):
        ordering = ["due_date"]
        verbose_name = "Reminder"

    def __str__(self):
        status = "✓" if self.is_completed else "○"
        return f"[{status}] {self.title} — {self.due_date}"

    @property
    def is_overdue(self):
        return not self.is_completed and self.due_date < timezone.now().date()


# ─── Vaccination ──────────────────────────────────────────────────────────────

class Vaccination(TimeStampedModel):
    """Vaccination schedule and records for the patient."""

    VACCINE_CHOICES = [
        ("tt1", "Tetanus Toxoid - 1st dose (TT1)"),
        ("tt2", "Tetanus Toxoid - 2nd dose (TT2)"),
        ("tt3", "Tetanus Toxoid - 3rd dose (TT3)"),
        ("td1", "Tetanus Diphtheria - 1st dose (Td1)"),
        ("td2", "Tetanus Diphtheria - 2nd dose (Td2)"),
        ("covid", "COVID-19 Vaccine"),
        ("influenza", "Influenza Vaccine"),
        ("hepatitis_b", "Hepatitis B Vaccine"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="vaccinations",
    )
    vaccine_name = models.CharField(max_length=50, choices=VACCINE_CHOICES)
    scheduled_date = models.DateField()
    administered_date = models.DateField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    administered_by = models.CharField(max_length=200, blank=True, help_text="Name of health worker.")
    facility = models.CharField(max_length=200, blank=True, help_text="Health facility name.")
    notes = models.TextField(blank=True)

    class Meta(TimeStampedModel.Meta):
        ordering = ["scheduled_date"]
        verbose_name = "Vaccination Record"

    def __str__(self):
        status = "✓" if self.is_completed else "Scheduled"
        return f"{self.get_vaccine_name_display()} — {status}"


# ─── Emergency Contacts ──────────────────────────────────────────────────────

class EmergencyContact(TimeStampedModel):
    """Patient emergency contacts."""

    RELATIONSHIP_CHOICES = [
        ("spouse", "Spouse / Partner"),
        ("parent", "Parent"),
        ("sibling", "Sibling"),
        ("friend", "Friend"),
        ("doctor", "Doctor"),
        ("health_facility", "Health Facility"),
        ("ambulance", "Ambulance Service"),
        ("other", "Other"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="emergency_contacts",
    )
    name = models.CharField(max_length=200)
    relationship = models.CharField(max_length=20, choices=RELATIONSHIP_CHOICES)
    phone = models.CharField(max_length=20)
    alternate_phone = models.CharField(max_length=20, blank=True)
    is_primary = models.BooleanField(default=False, help_text="Primary emergency contact.")

    class Meta(TimeStampedModel.Meta):
        ordering = ["-is_primary", "name"]
        verbose_name = "Emergency Contact"

    def __str__(self):
        return f"{self.name} ({self.get_relationship_display()}) — {self.phone}"


# ─── Consultation Requests ───────────────────────────────────────────────────

class ConsultationRequest(TimeStampedModel):
    """Patient request for doctor consultation."""

    STATUS_CHOICES = [
        ("pending", "Pending"),
        ("accepted", "Accepted"),
        ("completed", "Completed"),
        ("cancelled", "Cancelled"),
    ]

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="consultation_requests",
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="consultations_received",
    )
    reason = models.TextField(help_text="Reason for consultation.")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="pending")
    preferred_date = models.DateField(null=True, blank=True)
    doctor_notes = models.TextField(blank=True)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Consultation Request"

    def __str__(self):
        return f"Consultation: {self.patient.get_short_name()} → {self.doctor or 'Unassigned'} [{self.status}]"


# ─── Education Content ───────────────────────────────────────────────────────

class EducationContent(TimeStampedModel):
    """Health education articles / tips for awareness."""

    CATEGORY_CHOICES = [
        ("nutrition", "Nutrition & Diet"),
        ("exercise", "Exercise & Fitness"),
        ("danger_signs", "Danger Signs"),
        ("birth_prep", "Birth Preparedness"),
        ("postpartum", "Postpartum Care"),
        ("mental_health", "Mental Health"),
        ("breastfeeding", "Breastfeeding"),
        ("general", "General Health"),
    ]

    TRIMESTER_CHOICES = [
        (0, "All Trimesters"),
        (1, "First Trimester"),
        (2, "Second Trimester"),
        (3, "Third Trimester"),
    ]

    title = models.CharField(max_length=300)
    slug = models.SlugField(max_length=300, unique=True)
    category = models.CharField(max_length=30, choices=CATEGORY_CHOICES)
    trimester = models.PositiveSmallIntegerField(
        choices=TRIMESTER_CHOICES, default=0
    )
    content = models.TextField()
    summary = models.TextField(max_length=500, blank=True)
    image = models.ImageField(upload_to="education/", null=True, blank=True)
    is_published = models.BooleanField(default=True)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Education Content"
        verbose_name_plural = "Education Content"

    def __str__(self):
        return f"[{self.get_category_display()}] {self.title}"
