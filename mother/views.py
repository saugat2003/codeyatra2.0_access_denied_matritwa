"""
mother/views.py — Thin HTTP adapter layer for the Maternal Health bounded context.

Views are pure request/response handlers:
  1. Parse the HTTP request (path params, GET params, POST body).
  2. Delegate to an application service (command or query).
  3. Return a rendered template or HTTP redirect.

No business logic, no ORM queries, no domain rules live here.
"""

import logging
from datetime import date

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.shortcuts import get_object_or_404, redirect, render

from accounts.models import MotherProfile
from mother.application.commands import (
    CreateAwarenessProgramCommand,
    CreateConsultationCommand,
    RecordANCVisitCommand,
    RegisterMotherCommand,
    ResolveAlertCommand,
    TriggerSOSCommand,
    UpdateMotherPhotoCommand,
)
from mother.application.queries import (
    AlertsQueryService,
    DashboardQueryService,
    MonthlyReportQueryService,
    MotherListQueryService,
    RecordsDetailQueryService,
)
from mother.domain.services import PregnancyCalculator, SOSRiskEvaluator
from mother.domain.value_objects import Initials
from mother.forms import ANCVisitForm, AwarenessProgramForm, HospitalConsultationForm
from mother.models import ANCVisit, Alert, SOSEmergency

logger = logging.getLogger(__name__)

# ── Service singletons (stateless — safe to share across requests) ──
_dashboard_qs = DashboardQueryService()
_mother_list_qs = MotherListQueryService()
_records_qs = RecordsDetailQueryService()
_monthly_report_qs = MonthlyReportQueryService()
_alerts_qs = AlertsQueryService()

_register_mother_cmd = RegisterMotherCommand()
_record_anc_cmd = RecordANCVisitCommand()
_create_consultation_cmd = CreateConsultationCommand()
_create_awareness_cmd = CreateAwarenessProgramCommand()
_trigger_sos_cmd = TriggerSOSCommand()
_resolve_alert_cmd = ResolveAlertCommand()
_update_photo_cmd = UpdateMotherPhotoCommand()


# ── Helpers ──────────────────────────────────────────────────────


def _get_own_profile_or_404(user, pk: int) -> MotherProfile:
    """Return the MotherProfile if the user owns it, or raise 404."""
    if user.is_staff:
        return get_object_or_404(MotherProfile, pk=pk)
    return get_object_or_404(MotherProfile, pk=pk, registered_by=user)


# ── Index / landing ───────────────────────────────────────────────


def index(request):
    """Redirect authenticated users to the dashboard; others to login."""
    if request.user.is_authenticated:
        return redirect("main:dashboard")
    return redirect("accounts:login")


# ── FCHV Dashboard ────────────────────────────────────────────────


@login_required
def dashboard(request):
    """Main FCHV dashboard with summary statistics."""
    stats = _dashboard_qs.get_dashboard_stats(request.user)
    context = {
        "total_mothers": stats.total_mothers,
        "high_risk_count": stats.high_risk_count,
        "recent_visits": stats.recent_visits,
        "goal_progress": stats.goal_progress,
        "active_mothers": stats.active_mothers,
        "user": request.user,
    }
    return render(request, "mother/dashboard.html", context)


# ── Register Mother ───────────────────────────────────────────────


@login_required
def register_mother(request):
    """Single-page form for FCHV to register a new pregnant woman."""
    from mother.forms import MotherRegistrationForm

    if request.method == "POST":
        form = MotherRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            profile = _register_mother_cmd.execute(form=form, registered_by=request.user)
            messages.success(request, f"{profile.full_name} has been registered successfully!")
            return redirect("main:dashboard")
    else:
        form = MotherRegistrationForm()

    return render(request, "mother/register_mother.html", {"form": form})


# ── Mother List ───────────────────────────────────────────────────


@login_required
def mother_list(request):
    """List all registered mothers with search and risk-filter support."""
    search_query = request.GET.get("q", "").strip()
    risk_filter = request.GET.get("risk", "")

    mothers = _mother_list_qs.get_mother_list(
        request.user,
        search_query=search_query,
        risk_filter=risk_filter,
    )
    context = {
        "mothers": mothers,
        "search_query": search_query,
        "risk_filter": risk_filter,
    }
    return render(request, "mother/mother_list.html", context)


# ── Mother Profile ────────────────────────────────────────────────


@login_required
def mother_profile(request, pk):
    """Detailed profile view for a single mother."""
    profile = _get_own_profile_or_404(request.user, pk)

    visits = profile.anc_visits.order_by("visit_number")
    total_visits = visits.count()

    pw = PregnancyCalculator.get_pregnancy_week(profile.lmp_date, profile.pregnancy_week)
    edd = PregnancyCalculator.get_estimated_due_date(profile.lmp_date, profile.pregnancy_week)
    weeks = pw.value if pw else None

    has_danger = visits.filter(has_danger_signs=True).exists()
    risk_level = "HIGH RISK" if has_danger else "LOW RISK"
    trimester = pw.trimester if pw else ""

    context = {
        "profile": profile,
        "visits": visits,
        "total_visits": total_visits,
        "anc_progress_pct": min(100, int((total_visits / 8) * 100)),
        "weeks": weeks,
        "due_date": edd.value if edd else None,
        "initials": str(Initials.from_name(profile.full_name)),
        "risk_level": risk_level,
        "has_danger": has_danger,
        "trimester": trimester,
    }
    return render(request, "mother/mother_profile.html", context)


# ── Update ANC Visit ──────────────────────────────────────────────


@login_required
def update_anc_visit(request, pk):
    """Record a new ANC visit for the given mother profile."""
    profile = _get_own_profile_or_404(request.user, pk)
    last_visit = profile.anc_visits.order_by("-visit_number").first()
    next_number = (last_visit.visit_number + 1) if last_visit else 1

    if request.method == "POST":
        form = ANCVisitForm(request.POST)
        if form.is_valid():
            visit = _record_anc_cmd.execute(form=form, profile=profile, recorded_by=request.user)
            if visit.has_danger_signs:
                messages.warning(
                    request,
                    "⚠ Danger signs detected! Please refer to a specialist immediately.",
                )
            else:
                messages.success(request, f"ANC Visit {visit.visit_number} saved successfully.")
            return redirect("main:mother_profile", pk=profile.pk)
    else:
        form = ANCVisitForm()

    return render(
        request,
        "mother/update_anc_visit.html",
        {"form": form, "profile": profile, "visit_number": next_number},
    )


# ── Awareness Program ─────────────────────────────────────────────


@login_required
def awareness_program(request):
    """Create a new community awareness event."""
    mothers = MotherProfile.objects.filter(
        registration_completed=True, registered_by=request.user
    )

    if request.method == "POST":
        form = AwarenessProgramForm(request.POST)
        if form.is_valid():
            _create_awareness_cmd.execute(
                form=form,
                created_by=request.user,
                attendee_ids=request.POST.getlist("attendees"),
            )
            messages.success(request, "Awareness event created successfully!")
            return redirect("main:dashboard")
    else:
        form = AwarenessProgramForm()

    return render(request, "mother/awareness_program.html", {"form": form, "mothers": mothers})


# ── Hospital Consultation ─────────────────────────────────────────


@login_required
def hospital_consultation(request, pk):
    """View / create a hospital consultation referral for a mother."""
    profile = _get_own_profile_or_404(request.user, pk)
    visits = profile.anc_visits.order_by("-visit_number")
    latest_visit = visits.first()

    pw = PregnancyCalculator.get_pregnancy_week(profile.lmp_date, profile.pregnancy_week)
    active_symptoms = (latest_visit.symptoms or []) if latest_visit else []
    has_danger = latest_visit.has_danger_signs if latest_visit else False

    if request.method == "POST":
        form = HospitalConsultationForm(request.POST)
        if form.is_valid():
            _create_consultation_cmd.execute(
                form=form,
                profile=profile,
                referred_by=request.user,
            )
            messages.success(request, "Digital case summary sent successfully!")
            return redirect("main:mother_profile", pk=profile.pk)
    else:
        form = HospitalConsultationForm()

    context = {
        "form": form,
        "profile": profile,
        "initials": str(Initials.from_name(profile.full_name)),
        "weeks": pw.value if pw else None,
        "latest_visit": latest_visit,
        "active_symptoms": active_symptoms,
        "has_danger": has_danger,
    }
    return render(request, "mother/hospital_consultation.html", context)


# ── Update Profile Photo ──────────────────────────────────────────


@login_required
def update_photo(request, pk):
    """Replace a mother's profile photo."""
    profile = _get_own_profile_or_404(request.user, pk)

    if request.method == "POST":
        photo = request.FILES.get("photo")
        if photo:
            _update_photo_cmd.execute(profile=profile, new_photo=photo)
            messages.success(request, "Profile photo updated.")
        else:
            messages.error(request, "No image file was received.")

    return redirect("main:mother_profile", pk=pk)


# ── Monthly Reports ───────────────────────────────────────────────


@login_required
def monthly_reports(request):
    """Display monthly performance metrics and charts."""
    today = date.today()

    try:
        month = int(request.GET.get("month", today.month))
        year = int(request.GET.get("year", today.year))
    except (ValueError, TypeError):
        month, year = today.month, today.year

    data = _monthly_report_qs.get_report(request.user, month=month, year=year)

    context = {
        "total_mothers": data.total_mothers,
        "new_registrations": data.new_registrations,
        "total_anc_visits": data.total_anc_visits,
        "high_risk_count": data.high_risk_count,
        "stable_count": data.stable_count,
        "observation_count": data.observation_count,
        "weekly_chart_data": data.weekly_chart_data,
        "risk_distribution": data.risk_distribution,
        "goal_progress": data.goal_progress,
        "visit_target": data.visit_target,
        "completed_visits": data.total_anc_visits,
        "months_list": data.months_list,
        "current_month": data.current_month,
        "current_year": data.current_year,
        "current_month_label": data.current_month_label,
        "total_cases": data.total_mothers,
        "sos_count": data.sos_count,
    }
    return render(request, "mother/monthly_reports.html", context)


# ── Priority Alerts ───────────────────────────────────────────────


@login_required
def priority_alerts(request):
    """Display emergency SOS, high-risk monitoring, and missed appointments."""
    filter_type = request.GET.get("filter", "all")
    data = _alerts_qs.get_alerts_data(request.user, filter_type=filter_type)

    context = {
        "emergency_alert": data.emergency_alert,
        "high_risk_alerts": data.high_risk_alerts,
        "missed_appointments": data.missed_appointments,
        "total_alerts": data.total_alerts,
        "emergency_count": data.emergency_count,
        "high_risk_count": data.high_risk_count,
        "missed_count": data.missed_count,
        "filter_type": data.filter_type,
    }
    return render(request, "mother/prioroty_alerts.html", context)


# ── Records Detail ────────────────────────────────────────────────


@login_required
def records_detail(request):
    """Detailed mother records with search, filter support."""
    search_query = request.GET.get("q", "").strip()
    risk_filter = request.GET.get("risk", "all")

    records = _records_qs.get_records(
        request.user,
        search_query=search_query,
        risk_filter=risk_filter,
    )
    from mother.application.queries import _build_danger_ids, _get_volunteer_mother_ids
    vol_ids = _get_volunteer_mother_ids(request.user)
    high_risk_count = len(_build_danger_ids(vol_ids))

    context = {
        "records": records,
        "search_query": search_query,
        "risk_filter": risk_filter,
        "high_risk_count": high_risk_count,
        "user": request.user,
    }
    return render(request, "mother/mother_records_detail.html", context)


# ── SOS Views ─────────────────────────────────────────────────────


@login_required
def sos_trigger_page(request, pk):
    """Render the offline-first SOS trigger page."""
    mother = _get_own_profile_or_404(request.user, pk)
    danger_count = ANCVisit.objects.filter(mother=mother, has_danger_signs=True).count()
    risk_level = SOSRiskEvaluator.evaluate(
        danger_visit_count=danger_count,
        pregnancy_week=mother.pregnancy_week,
        age=mother.age,
        has_previous_complications=mother.has_previous_complications,
    )
    return render(request, "mother/sos_trigger.html", {"mother": mother, "risk_level": risk_level})


@login_required
def trigger_sos(request, pk):
    """Form-POST SOS trigger (non-JS fallback)."""
    profile = _get_own_profile_or_404(request.user, pk)

    if request.method == "POST":
        note = request.POST.get("note", "").strip()
        _trigger_sos_cmd.execute(profile=profile, triggered_by=request.user, note=note)
        messages.success(
            request,
            f"SOS alert triggered for {profile.full_name}. Emergency services notified.",
        )
        return redirect("main:priority_alerts")

    return redirect("main:mother_profile", pk=pk)


@login_required
def sos_history(request, pk):
    """Display the SOS emergency history for a specific mother."""
    mother = _get_own_profile_or_404(request.user, pk)
    emergencies = (
        SOSEmergency.objects.filter(mother=mother)
        .select_related("triggered_by", "resolved_by")
        .order_by("-triggered_at")
    )
    context = {
        "mother": mother,
        "emergencies": emergencies,
        "active_count": emergencies.filter(
            status__in=[SOSEmergency.Status.ACTIVE, SOSEmergency.Status.RESPONDING]
        ).count(),
    }
    return render(request, "mother/sos_history.html", context)


@login_required
def resolve_alert(request, pk):
    """Mark an alert as resolved."""
    alert = get_object_or_404(Alert, pk=pk)

    if request.method == "POST":
        try:
            _resolve_alert_cmd.execute(alert=alert, resolved_by=request.user)
            messages.success(request, "Alert marked as resolved.")
        except PermissionError as exc:
            messages.error(request, str(exc))

    return redirect("main:priority_alerts")