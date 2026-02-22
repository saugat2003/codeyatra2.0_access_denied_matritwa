from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from .forms import (
    DoctorOnboardingForm,
    FCHVOnboardingForm,
    LoginForm,
    PatientOnboardingForm,
    UserRegistrationForm,
)
from .models import DoctorProfile, FCHVProfile, PatientProfile

User = get_user_model()


# ── Registration ─────────────────────────────────────────────────────────────

def register(request):
    """User registration view — creates the User and redirects to onboarding."""
    if request.user.is_authenticated:
        return redirect("accounts:onboarding")

    form = UserRegistrationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(
            request,
            f"Welcome to Matritwa, {user.get_short_name()}! Let's set up your profile.",
        )
        return redirect("accounts:onboarding")

    return render(request, "accounts/register.html", {"form": form})


# ── Login / Logout ────────────────────────────────────────────────────────────

def user_login(request):
    """Login view."""
    if request.user.is_authenticated:
        return _role_redirect(request.user)

    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.get_user()
        login(request, user)
        messages.success(request, f"Welcome back, {user.get_short_name()}!")
        return _role_redirect(user)

    return render(request, "accounts/login.html", {"form": form})


def user_logout(request):
    """Logout view."""
    logout(request)
    messages.info(request, "You have been logged out.")
    return redirect("accounts:login")


# ── Onboarding ────────────────────────────────────────────────────────────────

@login_required
def onboarding(request):
    """
    Multi-role onboarding wizard.
    Shows the appropriate form based on the user's role.
    On success, marks user.is_onboarded = True and redirects to dashboard.
    """
    user = request.user

    if user.is_onboarded:
        return _role_redirect(user)

    form_class = _get_onboarding_form(user)
    existing_profile = _get_existing_profile(user)

    form = form_class(
        request.POST or None,
        instance=existing_profile,
    )

    if request.method == "POST" and form.is_valid():
        profile = form.save(commit=False)
        profile.user = user
        profile.save()
        user.is_onboarded = True
        user.save(update_fields=["is_onboarded"])
        messages.success(request, "Your profile is all set! Welcome to Matritwa 🌸")
        return _role_redirect(user)

    context = {
        "form": form,
        "role_label": user.get_role_display(),
        "step": "onboarding",
    }
    return render(request, "accounts/onboarding.html", context)


# ── Helpers ───────────────────────────────────────────────────────────────────

def _role_redirect(user):
    """Redirect to the correct dashboard based on user role."""
    if user.role == User.Role.DOCTOR:
        return redirect("main:index")   # swap for doctors_dashboard when ready
    if user.role == User.Role.FCHV:
        return redirect("main:index")   # swap for fchv_dashboard when ready
    return redirect("main:dashboard")


def _get_onboarding_form(user):
    if user.role == User.Role.DOCTOR:
        return DoctorOnboardingForm
    if user.role == User.Role.FCHV:
        return FCHVOnboardingForm
    return PatientOnboardingForm


def _get_existing_profile(user):
    """Return existing profile instance if any, else None."""
    if user.role == User.Role.DOCTOR:
        return DoctorProfile.objects.filter(user=user).first()
    if user.role == User.Role.FCHV:
        return FCHVProfile.objects.filter(user=user).first()
    return PatientProfile.objects.filter(user=user).first()
