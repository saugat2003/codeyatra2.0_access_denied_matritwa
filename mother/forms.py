"""Forms for the main app."""

from django import forms
from accounts.models import MotherProfile
from .models import ANCVisit, AwarenessProgram, HospitalConsultation


# ── Mother Registration (single-page by FCHV) ──────────────────


class MotherRegistrationForm(forms.ModelForm):
    """Single-page form for FCHV to register a pregnant woman."""

    class Meta:
        model = MotherProfile
        fields = [
            "full_name",
            "age",
            "phone",
            "pregnancy_week",
            "lmp_date",
            "is_first_pregnancy",
            "has_previous_complications",
            "blood_group",
            "medical_notes",
            "ward",
            "latitude",
            "longitude",
            "address",
        ]
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "placeholder": "Full name",
                    "class": "w-full rounded-xl px-4 py-3.5",
                }
            ),
            "age": forms.NumberInput(
                attrs={
                    "placeholder": "Age",
                    "min": "10",
                    "max": "60",
                    "class": "w-full rounded-xl px-4 py-3.5",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "placeholder": "Phone (optional)",
                    "class": "w-full rounded-xl px-4 py-3.5",
                }
            ),
            "pregnancy_week": forms.NumberInput(
                attrs={
                    "placeholder": "Current week (1-42)",
                    "min": "1",
                    "max": "42",
                    "class": "w-full rounded-xl px-4 py-3.5",
                }
            ),
            "lmp_date": forms.DateInput(
                attrs={
                    "type": "date",
                    "class": "w-full rounded-xl px-4 py-3.5",
                }
            ),
            "blood_group": forms.Select(
                attrs={
                    "class": "w-full rounded-xl px-4 py-3.5 appearance-none",
                }
            ),
            "medical_notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Pre-existing conditions, allergies…",
                    "class": "w-full rounded-xl px-4 py-3",
                }
            ),
            "ward": forms.TextInput(
                attrs={
                    "placeholder": "Ward / Municipality",
                    "class": "w-full rounded-xl px-4 py-3.5",
                }
            ),
            "address": forms.TextInput(
                attrs={
                    "placeholder": "Village / Tole / Address",
                    "class": "w-full rounded-xl px-4 py-3.5",
                }
            ),
            "latitude": forms.HiddenInput(),
            "longitude": forms.HiddenInput(),
        }


class ANCVisitForm(forms.ModelForm):
    """Form for recording an ANC visit update."""

    symptoms = forms.MultipleChoiceField(
        choices=ANCVisit.SYMPTOM_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        required=False,
    )

    class Meta:
        model = ANCVisit
        fields = ["weight_kg", "blood_pressure", "symptoms", "notes"]
        widgets = {
            "weight_kg": forms.NumberInput(
                attrs={
                    "placeholder": "e.g. 65.5",
                    "step": "0.1",
                    "class": "form-input w-full rounded-xl h-14 p-4",
                }
            ),
            "blood_pressure": forms.TextInput(
                attrs={
                    "placeholder": "e.g. 120/80",
                    "class": "form-input w-full rounded-xl h-14 p-4",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Additional observations...",
                    "class": "form-input w-full rounded-xl p-4",
                }
            ),
        }


class AwarenessProgramForm(forms.ModelForm):
    """Form for creating a community awareness event."""

    class Meta:
        model = AwarenessProgram
        fields = ["topic", "event_datetime", "location", "notes"]
        widgets = {
            "topic": forms.Select(
                attrs={"class": "w-full rounded-xl px-4 py-3.5 appearance-none"}
            ),
            "event_datetime": forms.DateTimeInput(
                attrs={
                    "type": "datetime-local",
                    "class": "w-full rounded-xl px-4 py-3.5",
                }
            ),
            "location": forms.TextInput(
                attrs={
                    "placeholder": "Enter community center or address",
                    "class": "w-full rounded-xl px-4 py-3.5 pl-11",
                }
            ),
            "notes": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Special instructions for attendees...",
                    "class": "w-full rounded-xl px-4 py-3",
                }
            ),
        }


class HospitalConsultationForm(forms.ModelForm):
    """Form for sending a consultation/referral."""

    class Meta:
        model = HospitalConsultation
        fields = ["reason", "symptoms", "recommendation"]
        widgets = {
            "reason": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Reason for consultation...",
                    "class": "w-full rounded-xl p-4",
                }
            ),
            "recommendation": forms.Textarea(
                attrs={
                    "rows": 3,
                    "placeholder": "Clinical recommendation...",
                    "class": "w-full rounded-xl p-4",
                }
            ),
        }
