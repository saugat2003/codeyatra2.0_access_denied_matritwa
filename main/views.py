from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (
    ConsultationRequestForm,
    DangerSignReportForm,
    EmergencyContactForm,
    HealthStreakForm,
    ReminderForm,
    SymptomLogForm,
    VaccinationForm,
)
from .models import (
    ConsultationRequest,
    DangerSignReport,
    EducationContent,
    EmergencyContact,
    HealthStreak,
    PregnancyMilestone,
    Reminder,
    SymptomLog,
    Vaccination,
)
from .utils import (
    get_days_remaining,
    get_expected_delivery_date,
    get_pregnancy_progress_percent,
    get_pregnancy_week,
    get_streak_count,
    get_trimester,
)


# ─────────────────────────────────────────────────────────────────────────────
# Public / Landing
# ─────────────────────────────────────────────────────────────────────────────


def index(request):
    """Render the landing page."""
    if request.user.is_authenticated:
        return redirect("main:dashboard")
    return render(request, "main/index.html")


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────


def _patient_context(user):
    """Build common pregnancy-related context from the patient's profile."""
    profile = getattr(user, "patient_profile", None)
    lmp = getattr(profile, "last_menstrual_period", None) if profile else None
    edd = getattr(profile, "expected_delivery_date", None) if profile else None

    # compute if LMP available
    if lmp and not edd:
        edd = get_expected_delivery_date(lmp)

    week = get_pregnancy_week(lmp) if lmp else 0
    trimester = get_trimester(week) if week else 0
    progress = get_pregnancy_progress_percent(week) if week else 0
    days_left = get_days_remaining(edd) if edd else 0

    return {
        "profile": profile,
        "lmp": lmp,
        "edd": edd,
        "week": week,
        "trimester": trimester,
        "progress": progress,
        "days_left": days_left,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Dashboard
# ─────────────────────────────────────────────────────────────────────────────


@login_required
def dashboard(request):
    """Patient welcome dashboard with pregnancy overview cards."""
    user = request.user
    ctx = _patient_context(user)

    # Quick summary counts
    ctx["upcoming_reminders"] = Reminder.objects.filter(
        user=user, is_completed=False, due_date__gte=timezone.now().date()
    ).count()
    ctx["pending_danger_signs"] = DangerSignReport.objects.filter(
        user=user, status="pending"
    ).count()
    ctx["streak_count"] = get_streak_count(
        HealthStreak.objects.filter(user=user)
    )
    ctx["recent_symptoms"] = SymptomLog.objects.filter(user=user)[:3]
    ctx["next_vaccination"] = (
        Vaccination.objects.filter(user=user, is_completed=False)
        .order_by("scheduled_date")
        .first()
    )

    # current milestone
    if ctx["week"]:
        ctx["current_milestone"] = PregnancyMilestone.objects.filter(
            week_number=ctx["week"]
        ).first()

    return render(request, "main/welcome_dashboard.html", ctx)


# ─────────────────────────────────────────────────────────────────────────────
# Pregnancy Timeline
# ─────────────────────────────────────────────────────────────────────────────


@login_required
def pregnancy_timeline(request):
    """Week-by-week pregnancy timeline with current-week highlight."""
    ctx = _patient_context(request.user)
    ctx["milestones"] = PregnancyMilestone.objects.all()
    return render(request, "main/pregnancy_timeline.html", ctx)


# ─────────────────────────────────────────────────────────────────────────────
# Health Streaks
# ─────────────────────────────────────────────────────────────────────────────


@login_required
def health_streaks(request):
    """Show health streak tracker + history."""
    user = request.user
    streaks = HealthStreak.objects.filter(user=user)
    today = timezone.now().date()
    today_streak = streaks.filter(date=today).first()
    streak_count = get_streak_count(streaks)

    ctx = {
        "streaks": streaks[:30],
        "today_streak": today_streak,
        "streak_count": streak_count,
        "today": today,
    }
    ctx.update(_patient_context(user))
    return render(request, "main/health_streaks_tracker.html", ctx)


@login_required
def log_health_streak(request):
    """Log or update today's health streak."""
    user = request.user
    today = timezone.now().date()
    instance = HealthStreak.objects.filter(user=user, date=today).first()

    if request.method == "POST":
        form = HealthStreakForm(request.POST, instance=instance)
        if form.is_valid():
            streak = form.save(commit=False)
            streak.user = user
            streak.save()
            messages.success(request, "Health streak logged! Keep it up! 🎯")
            return redirect("main:health_streaks")
    else:
        form = HealthStreakForm(instance=instance, initial={"date": today})

    return render(request, "main/log_health_streak.html", {"form": form})


# ─────────────────────────────────────────────────────────────────────────────
# Symptom Checker
# ─────────────────────────────────────────────────────────────────────────────


@login_required
def symptom_checker(request):
    """View symptom history + log new symptom."""
    user = request.user
    symptoms = SymptomLog.objects.filter(user=user)
    danger_symptoms = [s for s in symptoms if s.is_danger]

    ctx = {
        "symptoms": symptoms[:20],
        "danger_symptoms": danger_symptoms,
    }
    ctx.update(_patient_context(user))
    return render(request, "main/smart_symptom_checker.html", ctx)


@login_required
def log_symptom(request):
    """Log a new symptom."""
    if request.method == "POST":
        form = SymptomLogForm(request.POST)
        if form.is_valid():
            symptom = form.save(commit=False)
            symptom.user = request.user
            symptom.save()

            if symptom.is_danger:
                messages.warning(
                    request,
                    "⚠️ This symptom may be a danger sign. Please consult your "
                    "healthcare provider or report it immediately.",
                )
            else:
                messages.success(request, "Symptom logged successfully.")
            return redirect("main:symptom_checker")
    else:
        form = SymptomLogForm(initial={"date": timezone.now().date()})

    return render(request, "main/log_symptom.html", {"form": form})


# ─────────────────────────────────────────────────────────────────────────────
# Danger Sign Reports
# ─────────────────────────────────────────────────────────────────────────────


@login_required
def report_danger_sign(request):
    """Report a danger sign — high priority."""
    if request.method == "POST":
        form = DangerSignReportForm(request.POST)
        if form.is_valid():
            report = form.save(commit=False)
            report.user = request.user
            report.save()
            messages.warning(
                request,
                "🚨 Danger sign reported! Your FCHV / Doctor will be notified.",
            )
            return redirect("main:danger_sign_reported", pk=report.pk)
    else:
        form = DangerSignReportForm()

    return render(request, "main/report_danger_sign.html", {"form": form})


@login_required
def danger_sign_reported(request, pk):
    """Confirmation page after a danger sign is reported."""
    report = get_object_or_404(DangerSignReport, pk=pk, user=request.user)
    return render(request, "main/danger_sign_reported.html", {"report": report})


# ─────────────────────────────────────────────────────────────────────────────
# Reminders
# ─────────────────────────────────────────────────────────────────────────────


@login_required
def reminders(request):
    """View and create reminders."""
    user = request.user
    today = timezone.now().date()

    if request.method == "POST":
        form = ReminderForm(request.POST)
        if form.is_valid():
            reminder = form.save(commit=False)
            reminder.user = user
            reminder.save()
            messages.success(request, "Reminder added! ✅")
            return redirect("main:reminders")
    else:
        form = ReminderForm()

    upcoming = Reminder.objects.filter(user=user, is_completed=False, due_date__gte=today)
    overdue = Reminder.objects.filter(user=user, is_completed=False, due_date__lt=today)
    completed = Reminder.objects.filter(user=user, is_completed=True)[:10]

    ctx = {
        "form": form,
        "upcoming": upcoming,
        "overdue": overdue,
        "completed": completed,
        "today": today,
    }
    return render(request, "main/reminders_notifications.html", ctx)


@login_required
def complete_reminder(request, pk):
    """Mark a reminder as completed."""
    reminder = get_object_or_404(Reminder, pk=pk, user=request.user)
    reminder.is_completed = True
    reminder.save()
    messages.success(request, f'"{reminder.title}" marked as complete.')
    return redirect("main:reminders")


# ─────────────────────────────────────────────────────────────────────────────
# Vaccinations
# ─────────────────────────────────────────────────────────────────────────────


@login_required
def vaccination_details(request):
    """View vaccination schedule + add new."""
    user = request.user

    if request.method == "POST":
        form = VaccinationForm(request.POST)
        if form.is_valid():
            vacc = form.save(commit=False)
            vacc.user = user
            vacc.save()
            messages.success(request, "Vaccination record added.")
            return redirect("main:vaccination_details")
    else:
        form = VaccinationForm()

    upcoming = Vaccination.objects.filter(user=user, is_completed=False)
    completed = Vaccination.objects.filter(user=user, is_completed=True)

    ctx = {
        "form": form,
        "upcoming": upcoming,
        "completed": completed,
    }
    return render(request, "main/vaccination_details.html", ctx)


@login_required
def vaccination_history(request):
    """View completed vaccinations."""
    vaccinations = Vaccination.objects.filter(user=request.user, is_completed=True)
    return render(request, "main/vaccination_history.html", {"vaccinations": vaccinations})


@login_required
def confirm_vaccination(request, pk):
    """Mark a vaccination as administered."""
    vacc = get_object_or_404(Vaccination, pk=pk, user=request.user)
    vacc.is_completed = True
    vacc.administered_date = timezone.now().date()
    vacc.save()
    messages.success(request, f"{vacc.get_vaccine_name_display()} marked as administered! 💉")
    return redirect("main:vaccination_confirmation", pk=vacc.pk)


@login_required
def vaccination_confirmation(request, pk):
    """Confirmation page after vaccination."""
    vacc = get_object_or_404(Vaccination, pk=pk, user=request.user)
    return render(request, "main/vaccination_confirmation_success.html", {"vaccination": vacc})


# ─────────────────────────────────────────────────────────────────────────────
# Emergency Contacts
# ─────────────────────────────────────────────────────────────────────────────


@login_required
def emergency_contacts(request):
    """Manage emergency contacts."""
    user = request.user

    if request.method == "POST":
        form = EmergencyContactForm(request.POST)
        if form.is_valid():
            contact = form.save(commit=False)
            contact.user = user
            contact.save()
            messages.success(request, "Emergency contact added.")
            return redirect("main:emergency_contacts")
    else:
        form = EmergencyContactForm()

    contacts = EmergencyContact.objects.filter(user=user)
    primary_contact = contacts.filter(is_primary=True).first()

    ctx = {
        "form": form,
        "contacts": contacts,
        "primary_contact": primary_contact,
    }
    return render(request, "main/emergency_contacts.html", ctx)


@login_required
def delete_emergency_contact(request, pk):
    """Delete an emergency contact."""
    contact = get_object_or_404(EmergencyContact, pk=pk, user=request.user)
    contact.delete()
    messages.success(request, "Emergency contact removed.")
    return redirect("main:emergency_contacts")


@login_required
def emergency_sos(request):
    """Emergency SOS details page with primary contact info."""
    user = request.user
    contacts = EmergencyContact.objects.filter(user=user)
    primary_contact = contacts.filter(is_primary=True).first()

    ctx = {
        "contacts": contacts,
        "primary_contact": primary_contact,
    }
    ctx.update(_patient_context(user))
    return render(request, "main/emergency_sos_details.html", ctx)


# ─────────────────────────────────────────────────────────────────────────────
# Doctor Consultation
# ─────────────────────────────────────────────────────────────────────────────


@login_required
def doctor_consultation(request):
    """Request a consultation with a doctor."""
    user = request.user

    if request.method == "POST":
        form = ConsultationRequestForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.patient = user
            consultation.save()
            messages.success(
                request,
                "Consultation request submitted! A doctor will review it soon.",
            )
            return redirect("main:doctor_consultation")
    else:
        form = ConsultationRequestForm()

    consultations = ConsultationRequest.objects.filter(patient=user)

    ctx = {
        "form": form,
        "consultations": consultations,
    }
    return render(request, "main/doctor_consultation.html", ctx)


# ─────────────────────────────────────────────────────────────────────────────
# Awareness / Education
# ─────────────────────────────────────────────────────────────────────────────


@login_required
def awareness_education(request):
    """Browse health education content, filtered by trimester if available."""
    user = request.user
    ctx = _patient_context(user)
    trimester = ctx.get("trimester", 0)

    category = request.GET.get("category", "")
    articles = EducationContent.objects.filter(is_published=True)

    if category:
        articles = articles.filter(category=category)

    # Show articles matching current trimester + general ones
    if trimester:
        articles = articles.filter(trimester__in=[0, trimester])

    ctx["articles"] = articles
    ctx["selected_category"] = category
    ctx["categories"] = EducationContent.CATEGORY_CHOICES
    return render(request, "main/awareness_education.html", ctx)


@login_required
def education_detail(request, slug):
    """View a single education article."""
    article = get_object_or_404(EducationContent, slug=slug, is_published=True)
    return render(request, "main/education_detail.html", {"article": article})
