from django.db import models


class TimeStampedModel(models.Model):
    """Abstract base model with created/updated timestamps."""

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class ANCVisit(TimeStampedModel):
    """Antenatal Care visit record for a mother."""

    mother = models.ForeignKey(
        "accounts.MotherProfile",
        on_delete=models.CASCADE,
        related_name="anc_visits",
    )
    visit_number = models.PositiveIntegerField(default=1)
    visit_date = models.DateField(auto_now_add=True)

    # Vitals
    weight_kg = models.DecimalField(
        max_digits=5, decimal_places=1, null=True, blank=True
    )
    blood_pressure = models.CharField(max_length=20, blank=True)

    # Symptoms
    SYMPTOM_CHOICES = [
        ("mild_nausea", "Mild Nausea"),
        ("severe_headache", "Severe Headache"),
        ("blurred_vision", "Blurred Vision"),
        ("fever_chills", "Fever / Chills"),
        ("swollen_feet", "Swollen Feet"),
        ("none", "No Symptoms Observed"),
    ]
    symptoms = models.JSONField(default=list, blank=True)

    # Danger-sign flag (auto-set when danger symptoms selected)
    has_danger_signs = models.BooleanField(default=False)

    notes = models.TextField(blank=True)
    recorded_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recorded_visits",
    )

    class Meta(TimeStampedModel.Meta):
        verbose_name = "ANC Visit"
        verbose_name_plural = "ANC Visits"
        unique_together = ("mother", "visit_number")

    def __str__(self):
        return f"Visit {self.visit_number} — {self.mother.full_name}"

    DANGER_SYMPTOMS = {"severe_headache", "blurred_vision", "fever_chills"}

    def save(self, *args, **kwargs):
        self.has_danger_signs = bool(
            set(self.symptoms or []) & self.DANGER_SYMPTOMS
        )
        super().save(*args, **kwargs)


class AwarenessProgram(TimeStampedModel):
    """Community awareness/education event."""

    TOPIC_CHOICES = [
        ("nutrition", "Nutrition & Healthy Eating"),
        ("hygiene", "Postnatal Hygiene"),
        ("mental_health", "Maternal Mental Health"),
        ("vaccination", "Childhood Vaccinations"),
    ]

    topic = models.CharField(max_length=50, choices=TOPIC_CHOICES)
    event_datetime = models.DateTimeField()
    location = models.CharField(max_length=255)
    notes = models.TextField(blank=True)

    attendees = models.ManyToManyField(
        "accounts.MotherProfile",
        blank=True,
        related_name="awareness_programs",
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="created_programs",
    )

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Awareness Program"

    def __str__(self):
        return f"{self.get_topic_display()} — {self.event_datetime:%Y-%m-%d}"


class HospitalConsultation(TimeStampedModel):
    """Health-post / hospital consultation referral."""

    mother = models.ForeignKey(
        "accounts.MotherProfile",
        on_delete=models.CASCADE,
        related_name="consultations",
    )
    reason = models.TextField()
    symptoms = models.JSONField(default=list, blank=True)
    recommendation = models.TextField(blank=True)
    reference_id = models.CharField(max_length=30, blank=True)
    is_synced = models.BooleanField(default=False)

    referred_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="referrals",
    )

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Hospital Consultation"

    def __str__(self):
        return f"Consultation — {self.mother.full_name} ({self.created_at:%Y-%m-%d})"


class Alert(TimeStampedModel):
    """Emergency alerts and notifications for FCHV monitoring."""

    class AlertType(models.TextChoices):
        EMERGENCY_SOS = "sos", "Emergency SOS"
        HIGH_RISK = "high_risk", "High Risk"
        MISSED_VISIT = "missed", "Missed Appointment"
        SYSTEM = "system", "System Update"

    class Priority(models.TextChoices):
        CRITICAL = "critical", "Critical"
        HIGH = "high", "High"
        MEDIUM = "medium", "Medium"
        LOW = "low", "Low"

    mother = models.ForeignKey(
        "accounts.MotherProfile",
        on_delete=models.CASCADE,
        related_name="alerts",
        null=True,
        blank=True,
    )
    alert_type = models.CharField(
        max_length=20,
        choices=AlertType.choices,
        default=AlertType.HIGH_RISK,
    )
    priority = models.CharField(
        max_length=10,
        choices=Priority.choices,
        default=Priority.MEDIUM,
    )
    title = models.CharField(max_length=255)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    is_resolved = models.BooleanField(default=False)

    assigned_to = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_alerts",
    )

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Alert"
        indexes = [
            models.Index(fields=["alert_type", "is_resolved"]),
            models.Index(fields=["priority", "-created_at"]),
        ]

    def __str__(self):
        return f"[{self.get_priority_display()}] {self.title}"


class ScheduledVisit(TimeStampedModel):
    """Scheduled ANC/PNC visits for mothers."""

    class VisitType(models.TextChoices):
        ANC = "anc", "Antenatal Care"
        PNC = "pnc", "Postnatal Care"
        FOLLOWUP = "followup", "Follow-up"

    mother = models.ForeignKey(
        "accounts.MotherProfile",
        on_delete=models.CASCADE,
        related_name="scheduled_visits",
    )
    visit_type = models.CharField(
        max_length=10,
        choices=VisitType.choices,
        default=VisitType.ANC,
    )
    visit_number = models.PositiveIntegerField(default=1)
    scheduled_date = models.DateField()
    scheduled_time = models.TimeField(null=True, blank=True)
    is_completed = models.BooleanField(default=False)
    completed_visit = models.ForeignKey(
        "ANCVisit",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="scheduled_for",
    )
    notes = models.TextField(blank=True)

    class Meta(TimeStampedModel.Meta):
        verbose_name = "Scheduled Visit"
        ordering = ["scheduled_date", "scheduled_time"]
        indexes = [
            models.Index(fields=["scheduled_date", "is_completed"]),
        ]

    def __str__(self):
        return f"{self.get_visit_type_display()} {self.visit_number} — {self.mother.full_name}"

    @property
    def is_overdue(self):
        from datetime import date
        return not self.is_completed and self.scheduled_date < date.today()


class MonthlyReport(TimeStampedModel):
    """Monthly performance metrics snapshot for reporting."""

    year = models.PositiveIntegerField()
    month = models.PositiveIntegerField()  # 1-12
    
    # Registration metrics
    total_registrations = models.PositiveIntegerField(default=0)
    new_registrations = models.PositiveIntegerField(default=0)
    
    # Visit metrics
    total_anc_visits = models.PositiveIntegerField(default=0)
    completed_visits = models.PositiveIntegerField(default=0)
    missed_visits = models.PositiveIntegerField(default=0)
    
    # Risk metrics
    high_risk_cases = models.PositiveIntegerField(default=0)
    stable_cases = models.PositiveIntegerField(default=0)
    observation_cases = models.PositiveIntegerField(default=0)
    
    # Weekly breakdown (JSON: {"week1": 10, "week2": 15, ...})
    weekly_registrations = models.JSONField(default=dict)
    
    # Goal tracking
    visit_target = models.PositiveIntegerField(default=50)

    generated_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="generated_reports",
    )

    class Meta:
        verbose_name = "Monthly Report"
        unique_together = ("year", "month")
        ordering = ["-year", "-month"]

    def __str__(self):
        return f"Report {self.year}-{self.month:02d}"

    @property
    def goal_progress(self):
        if self.visit_target == 0:
            return 0
        return min(100, int((self.completed_visits / self.visit_target) * 100))
