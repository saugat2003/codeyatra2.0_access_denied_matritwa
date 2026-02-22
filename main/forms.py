"""Forms for the main app."""

from django import forms

from .models import (
    ConsultationRequest,
    DangerSignReport,
    EmergencyContact,
    HealthStreak,
    Reminder,
    SymptomLog,
    Vaccination,
)


class HealthStreakForm(forms.ModelForm):
    class Meta:
        model = HealthStreak
        fields = [
            "date",
            "took_vitamins",
            "exercised",
            "drank_water",
            "ate_balanced_meal",
            "slept_well",
            "notes",
        ]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2, "placeholder": "Any notes…"}),
        }


class SymptomLogForm(forms.ModelForm):
    class Meta:
        model = SymptomLog
        fields = ["symptom", "severity", "description", "date"]
        widgets = {
            "date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 3, "placeholder": "Describe the symptom…"}),
        }


class DangerSignReportForm(forms.ModelForm):
    class Meta:
        model = DangerSignReport
        fields = ["danger_sign", "description"]
        widgets = {
            "description": forms.Textarea(
                attrs={"rows": 3, "placeholder": "Provide more details…"}
            ),
        }


class ReminderForm(forms.ModelForm):
    class Meta:
        model = Reminder
        fields = ["reminder_type", "title", "description", "due_date"]
        widgets = {
            "due_date": forms.DateInput(attrs={"type": "date"}),
            "description": forms.Textarea(attrs={"rows": 2}),
        }


class VaccinationForm(forms.ModelForm):
    class Meta:
        model = Vaccination
        fields = [
            "vaccine_name",
            "scheduled_date",
            "administered_date",
            "administered_by",
            "facility",
            "notes",
        ]
        widgets = {
            "scheduled_date": forms.DateInput(attrs={"type": "date"}),
            "administered_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 2}),
        }


class EmergencyContactForm(forms.ModelForm):
    class Meta:
        model = EmergencyContact
        fields = ["name", "relationship", "phone", "alternate_phone", "is_primary"]
        widgets = {
            "phone": forms.TextInput(attrs={"placeholder": "+977-XXXXXXXXXX"}),
            "alternate_phone": forms.TextInput(attrs={"placeholder": "Optional"}),
        }


class ConsultationRequestForm(forms.ModelForm):
    class Meta:
        model = ConsultationRequest
        fields = ["reason", "preferred_date"]
        widgets = {
            "reason": forms.Textarea(attrs={"rows": 3, "placeholder": "Reason for consultation…"}),
            "preferred_date": forms.DateInput(attrs={"type": "date"}),
        }
