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
