"""
accounts/views.py — Thin view layer for the Identity bounded context.

Views are pure HTTP adapters: they parse the request, call an application
service, and return a rendered response or redirect.  No business logic lives
here.
"""

import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render

from .services import AuthenticationService, RegistrationError, VolunteerRegistrationService

logger = logging.getLogger(__name__)

_auth_service = AuthenticationService()
_registration_service = VolunteerRegistrationService()


# ── Login ────────────────────────────────────────────────────────


def login_view(request):
    """Authenticate an FCHV volunteer or admin and redirect to the dashboard."""
    if request.user.is_authenticated:
        return redirect("main:dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        password = request.POST.get("password", "")

        success = _auth_service.login_user(request, username, password)
        if success:
            return redirect("main:dashboard")

        messages.error(request, "Invalid username or password.")

    return render(request, "accounts/login_page.html")


# ── Register ─────────────────────────────────────────────────────


def register_view(request):
    """Self-registration page for FCHV volunteers."""
    if request.user.is_authenticated:
        return redirect("main:dashboard")

    if request.method == "POST":
        try:
            user = _registration_service.register(
                username=request.POST.get("username", "").strip(),
                password1=request.POST.get("password1", ""),
                password2=request.POST.get("password2", ""),
                organization=request.POST.get("organization", "").strip(),
                education=request.POST.get("education", "").strip(),
                age=request.POST.get("age", "").strip(),
            )
            _auth_service.login_user(request, user.username, request.POST.get("password1", ""))
            messages.success(request, f"Welcome, {user.username}! Your account has been created.")
            return redirect("main:dashboard")

        except RegistrationError as exc:
            for err in exc.errors:
                messages.error(request, err)

    return render(request, "accounts/register_volunteer.html")


# ── Logout ───────────────────────────────────────────────────────


@login_required
def logout_view(request):
    """Log out the current user and redirect to the login page."""
    _auth_service.logout_user(request)
    messages.success(request, "You have been signed out.")
    return redirect("accounts:login")
