from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm
from django.utils.translation import gettext_lazy as _

from .models import DoctorProfile, FCHVProfile, PatientProfile

User = get_user_model()


class UserRegistrationForm(forms.ModelForm):
    """Step 1: basic credentials + role selection."""

    password1 = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "Create a password"}),
    )
    password2 = forms.CharField(
        label=_("Confirm Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "Repeat the password"}),
    )

    class Meta:
        model = User
        fields = ["first_name", "last_name", "email", "phone", "role"]
        widgets = {
            "first_name": forms.TextInput(attrs={"placeholder": "First name"}),
            "last_name": forms.TextInput(attrs={"placeholder": "Last name"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email address"}),
            "phone": forms.TextInput(attrs={"placeholder": "+977-XXXXXXXXXX"}),
            "role": forms.RadioSelect(),
        }

    def clean_email(self):
        email = self.cleaned_data.get("email").lower()
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError(
                _("An account with this email already exists.")
            )
        return email

    def clean(self):
        cleaned = super().clean()
        p1 = cleaned.get("password1")
        p2 = cleaned.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", _("Passwords do not match."))
        return cleaned

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password1"])
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    """Login form using email."""

    username = forms.EmailField(
        label=_("Email"),
        widget=forms.EmailInput(attrs={"placeholder": "Email address", "autofocus": True}),
    )
    password = forms.CharField(
        label=_("Password"),
        widget=forms.PasswordInput(attrs={"placeholder": "Password"}),
    )

    error_messages = {
        "invalid_login": _(
            "Please enter a correct email and password. "
            "Note that both fields may be case-sensitive."
        ),
        "inactive": _("This account is inactive."),
    }


# ── Onboarding forms ────────────────────────────────────────────────────────

class PatientOnboardingForm(forms.ModelForm):
    """Onboarding details for patients."""

    class Meta:
        model = PatientProfile
        fields = [
            "date_of_birth",
            "blood_group",
            "address",
            "district",
            "province",
            "last_menstrual_period",
            "gravida",
            "parity",
        ]
        widgets = {
            "date_of_birth": forms.DateInput(attrs={"type": "date"}),
            "last_menstrual_period": forms.DateInput(attrs={"type": "date"}),
            "address": forms.Textarea(attrs={"rows": 3, "placeholder": "Full address"}),
            "district": forms.TextInput(attrs={"placeholder": "e.g. Kathmandu"}),
            "province": forms.TextInput(attrs={"placeholder": "e.g. Bagmati"}),
        }


class DoctorOnboardingForm(forms.ModelForm):
    """Onboarding details for doctors."""

    class Meta:
        model = DoctorProfile
        fields = [
            "specialization",
            "license_number",
            "hospital_name",
            "years_of_experience",
            "available_for_consultation",
        ]
        widgets = {
            "specialization": forms.TextInput(attrs={"placeholder": "e.g. Gynecology"}),
            "license_number": forms.TextInput(attrs={"placeholder": "NMC license number"}),
            "hospital_name": forms.TextInput(attrs={"placeholder": "Hospital / Clinic name"}),
        }


class FCHVOnboardingForm(forms.ModelForm):
    """Onboarding details for FCHV workers."""

    class Meta:
        model = FCHVProfile
        fields = ["ward_number", "municipality", "district", "years_active"]
        widgets = {
            "ward_number": forms.TextInput(attrs={"placeholder": "Ward no."}),
            "municipality": forms.TextInput(attrs={"placeholder": "Municipality"}),
            "district": forms.TextInput(attrs={"placeholder": "District"}),
        }
