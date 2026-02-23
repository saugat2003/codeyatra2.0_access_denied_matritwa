import uuid
from datetime import date, timedelta
from collections import defaultdict

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from accounts.models import MotherProfile
from .forms import ANCVisitForm, AwarenessProgramForm, HospitalConsultationForm
from .models import ANCVisit, Alert, ScheduledVisit, SOSEmergency


# ── Index / Landing ─────────────────────────────────────────────


def index(request):
    """Redirect to login or the appropriate dashboard."""
    if request.user.is_authenticated:
        return redirect("main:dashboard")
    return redirect("accounts:login")


# ── FCHV Dashboard ──────────────────────────────────────────────


@login_required
def dashboard(request):
    """Main FCHV dashboard with summary statistics."""
    mothers = MotherProfile.objects.filter(registration_completed=True, registered_by=request.user)
    total_mothers = mothers.count()
    volunteer_mother_ids = mothers.values_list("pk", flat=True)

    # High-risk: mothers who have had any ANC visit with danger signs
    high_risk_ids = set(
        ANCVisit.objects.filter(has_danger_signs=True, mother_id__in=volunteer_mother_ids)
        .values_list("mother_id", flat=True)
        .distinct()
    )
    high_risk_count = mothers.filter(pk__in=high_risk_ids).count()

    # Recent ANC visits (for this volunteer's mothers only)
    recent_visits = (
        ANCVisit.objects.filter(mother_id__in=volunteer_mother_ids)
        .select_related("mother")
        .order_by("-created_at")[:5]
    )

    # Monthly goal progress (percentage of this volunteer's mothers with ≥1 visit)
    mothers_with_visits = (
        ANCVisit.objects.filter(mother_id__in=volunteer_mother_ids)
        .values("mother_id").distinct().count()
    )
    goal_progress = (
        int((mothers_with_visits / total_mothers) * 100)
        if total_mothers > 0
        else 0
    )

    # Active mothers — most recently registered, up to 5
    recent_mothers = mothers.order_by("-created_at")[:5]
    active_mothers = []
    for m in recent_mothers:
        initials = "".join(w[0].upper() for w in m.full_name.split()[:2]) if m.full_name else "?"
        weeks = _pregnancy_weeks(m)
        risk = "high" if m.pk in high_risk_ids else "stable"
        active_mothers.append({
            "profile": m,
            "initials": initials,
            "weeks": weeks,
            "risk": risk,
        })

    context = {
        "total_mothers": total_mothers,
        "high_risk_count": high_risk_count,
        "recent_visits": recent_visits,
        "goal_progress": goal_progress,
        "active_mothers": active_mothers,
        "user": request.user,
    }
    return render(request, "mother/dashboard.html", context)


# ── Register Mother (FCHV only) ────────────────────────────────


@login_required
def register_mother(request):
    """Single-page form for FCHV to register a new pregnant woman."""
    from .forms import MotherRegistrationForm

    if request.method == "POST":
        form = MotherRegistrationForm(request.POST, request.FILES)
        if form.is_valid():
            profile = form.save(commit=False)
            profile.registered_by = request.user
            profile.registration_completed = True
            profile.save()
            messages.success(
                request,
                f"{profile.full_name} has been registered successfully!",
            )
            return redirect("main:dashboard")
    else:
        form = MotherRegistrationForm()

    return render(request, "mother/register_mother.html", {"form": form})

# ── Update Profile Photo ──────────────────────────────────────────


@login_required
def update_photo(request, pk):
    """Update the profile photo for a mother."""
    if request.user.is_staff:
        profile = get_object_or_404(MotherProfile, pk=pk)
    else:
        profile = get_object_or_404(MotherProfile, pk=pk, registered_by=request.user)

    if request.method == "POST" and request.FILES.get("photo"):
        # Delete old photo file if it exists
        if profile.photo:
            profile.photo.delete(save=False)
        profile.photo = request.FILES["photo"]
        profile.save(update_fields=["photo"])
        messages.success(request, "Profile photo updated.")
    elif request.method == "POST":
        messages.error(request, "No image file was received.")

    return redirect("main:mother_profile", pk=pk)

# ── Mother List ─────────────────────────────────────────────────


@login_required
def mother_list(request):
    """List all registered mothers with search & risk-filter support."""
    mothers = MotherProfile.objects.filter(registration_completed=True, registered_by=request.user)

    # Search
    q = request.GET.get("q", "").strip()
    if q:
        mothers = mothers.filter(
            Q(full_name__icontains=q)
            | Q(ward__icontains=q)
            | Q(phone__icontains=q)
        )

    # Risk filter
    risk_filter = request.GET.get("risk", "")
    if risk_filter == "high":
        high_risk_ids = (
            ANCVisit.objects.filter(has_danger_signs=True)
            .values_list("mother_id", flat=True)
            .distinct()
        )
        mothers = mothers.filter(pk__in=high_risk_ids)
    elif risk_filter == "stable":
        high_risk_ids = (
            ANCVisit.objects.filter(has_danger_signs=True)
            .values_list("mother_id", flat=True)
            .distinct()
        )
        mothers = mothers.exclude(pk__in=high_risk_ids)

    # Annotate each mother with visit count & risk status
    mothers = mothers.annotate(visit_count=Count("anc_visits"))

    # Build risk map
    danger_mother_ids = set(
        ANCVisit.objects.filter(has_danger_signs=True)
        .values_list("mother_id", flat=True)
    )

    mother_data = []
    for m in mothers:
        weeks = _pregnancy_weeks(m)
        initials = "".join(w[0].upper() for w in m.full_name.split()[:2]) if m.full_name else "?"
        risk = "high" if m.pk in danger_mother_ids else "stable"
        mother_data.append({
            "profile": m,
            "initials": initials,
            "weeks": weeks,
            "risk": risk,
            "visit_count": m.visit_count,
        })

    context = {
        "mothers": mother_data,
        "search_query": q,
        "risk_filter": risk_filter,
    }
    return render(request, "mother/mother_list.html", context)


# ── Mother Profile ──────────────────────────────────────────────


@login_required
def mother_profile(request, pk):
    """Detailed profile view for a single mother."""
    if request.user.is_staff:
        profile = get_object_or_404(MotherProfile, pk=pk)
    else:
        profile = get_object_or_404(MotherProfile, pk=pk, registered_by=request.user)

    visits = profile.anc_visits.order_by("visit_number")
    total_visits = visits.count()
    weeks = _pregnancy_weeks(profile)
    due_date = _estimated_due_date(profile)
    initials = "".join(w[0].upper() for w in profile.full_name.split()[:2]) if profile.full_name else "?"

    # Risk assessment
    has_danger = visits.filter(has_danger_signs=True).exists()
    risk_level = "HIGH RISK" if has_danger else "LOW RISK"

    # Trimester
    if weeks and weeks <= 12:
        trimester = "1st Trimester"
    elif weeks and weeks <= 27:
        trimester = "2nd Trimester"
    elif weeks:
        trimester = "3rd Trimester"
    else:
        trimester = ""

    context = {
        "profile": profile,
        "visits": visits,
        "total_visits": total_visits,
        "anc_progress_pct": min(100, int((total_visits / 8) * 100)),
        "weeks": weeks,
        "due_date": due_date,
        "initials": initials,
        "risk_level": risk_level,
        "has_danger": has_danger,
        "trimester": trimester,
    }
    return render(request, "mother/mother_profile.html", context)


# ── Update ANC Visit ────────────────────────────────────────────


@login_required
def update_anc_visit(request, pk):
    """Record a new ANC visit for the given mother profile."""
    if request.user.is_staff:
        profile = get_object_or_404(MotherProfile, pk=pk)
    else:
        profile = get_object_or_404(MotherProfile, pk=pk, registered_by=request.user)

    # Determine next visit number
    last_visit = profile.anc_visits.order_by("-visit_number").first()
    next_number = (last_visit.visit_number + 1) if last_visit else 1

    if request.method == "POST":
        form = ANCVisitForm(request.POST)
        if form.is_valid():
            visit = form.save(commit=False)
            visit.mother = profile
            visit.visit_number = next_number
            visit.recorded_by = request.user
            visit.save()

            if visit.has_danger_signs:
                messages.warning(
                    request,
                    "⚠ Danger signs detected! Please refer to a specialist immediately.",
                )
            else:
                messages.success(request, f"ANC Visit {next_number} saved successfully.")

            return redirect("main:mother_profile", pk=profile.pk)
    else:
        form = ANCVisitForm()

    context = {
        "form": form,
        "profile": profile,
        "visit_number": next_number,
    }
    return render(request, "mother/update_anc_visit.html", context)


# ── Awareness Program ───────────────────────────────────────────


@login_required
def awareness_program(request):
    """Create a new community awareness event."""
    mothers = MotherProfile.objects.filter(registration_completed=True, registered_by=request.user)

    if request.method == "POST":
        form = AwarenessProgramForm(request.POST)
        if form.is_valid():
            program = form.save(commit=False)
            program.created_by = request.user
            program.save()

            # Attach selected attendees
            attendee_ids = request.POST.getlist("attendees")
            if attendee_ids:
                program.attendees.set(attendee_ids)

            messages.success(request, "Awareness event created successfully!")
            return redirect("main:dashboard")
    else:
        form = AwarenessProgramForm()

    context = {
        "form": form,
        "mothers": mothers,
    }
    return render(request, "mother/awareness_program.html", context)


# ── Hospital Consultation ───────────────────────────────────────


@login_required
def hospital_consultation(request, pk):
    """View / create a hospital consultation referral for a mother."""
    if request.user.is_staff:
        profile = get_object_or_404(MotherProfile, pk=pk)
    else:
        profile = get_object_or_404(MotherProfile, pk=pk, registered_by=request.user)
    visits = profile.anc_visits.order_by("-visit_number")
    latest_visit = visits.first()
    weeks = _pregnancy_weeks(profile)
    initials = "".join(w[0].upper() for w in profile.full_name.split()[:2]) if profile.full_name else "?"

    # Aggregate current symptoms
    active_symptoms = []
    if latest_visit and latest_visit.symptoms:
        active_symptoms = latest_visit.symptoms

    has_danger = latest_visit.has_danger_signs if latest_visit else False

    if request.method == "POST":
        form = HospitalConsultationForm(request.POST)
        if form.is_valid():
            consultation = form.save(commit=False)
            consultation.mother = profile
            consultation.referred_by = request.user
            consultation.reference_id = f"CT-{uuid.uuid4().hex[:5].upper()}-X"
            consultation.is_synced = True
            consultation.save()

            messages.success(request, "Digital case summary sent successfully!")
            return redirect("main:mother_profile", pk=profile.pk)
    else:
        form = HospitalConsultationForm()

    context = {
        "form": form,
        "profile": profile,
        "initials": initials,
        "weeks": weeks,
        "latest_visit": latest_visit,
        "active_symptoms": active_symptoms,
        "has_danger": has_danger,
    }
    return render(request, "mother/hospital_consultation.html", context)


# ── Helper utilities ────────────────────────────────────────────


def _pregnancy_weeks(profile):
    """Calculate current pregnancy week from LMP or stored week."""
    if profile.lmp_date:
        delta = date.today() - profile.lmp_date
        return max(1, delta.days // 7)
    return profile.pregnancy_week


def _estimated_due_date(profile):
    """Naegele's rule: LMP + 280 days."""
    if profile.lmp_date:
        return profile.lmp_date + timedelta(days=280)
    if profile.pregnancy_week:
        remaining = 40 - profile.pregnancy_week
        return date.today() + timedelta(weeks=remaining)
    return None


def _get_initials(name: str) -> str:
    """Extract initials from a full name."""
    if not name:
        return "?"
    return "".join(w[0].upper() for w in name.split()[:2])


def _get_risk_status(mother_id: int, danger_ids: set) -> str:
    """Determine risk status from danger set."""
    return "high" if mother_id in danger_ids else "stable"


# ── Monthly Reports View ────────────────────────────────────────


@login_required
def monthly_reports(request):
    """Display monthly performance metrics and charts."""
    today = date.today()
    current_month = request.GET.get("month", today.month)
    current_year = request.GET.get("year", today.year)

    try:
        current_month = int(current_month)
        current_year = int(current_year)
    except (ValueError, TypeError):
        current_month = today.month
        current_year = today.year

    # Date range for the month
    month_start = date(current_year, current_month, 1)
    if current_month == 12:
        month_end = date(current_year + 1, 1, 1) - timedelta(days=1)
    else:
        month_end = date(current_year, current_month + 1, 1) - timedelta(days=1)

    # All mothers registered by this volunteer
    all_mothers = MotherProfile.objects.filter(registration_completed=True, registered_by=request.user)
    total_mothers = all_mothers.count()

    # New registrations this month
    new_registrations = all_mothers.filter(
        created_at__date__gte=month_start,
        created_at__date__lte=month_end,
    ).count()

    # ANC visits this month (for mothers registered by this volunteer)
    volunteer_mother_ids = all_mothers.values_list("pk", flat=True)
    month_visits = ANCVisit.objects.filter(
        mother_id__in=volunteer_mother_ids,
        visit_date__gte=month_start,
        visit_date__lte=month_end,
    )
    total_anc_visits = month_visits.count()

    # High-risk cases (scoped to this volunteer's mothers)
    danger_mother_ids = set(
        ANCVisit.objects.filter(has_danger_signs=True, mother_id__in=volunteer_mother_ids)
        .values_list("mother_id", flat=True)
    )
    high_risk_count = all_mothers.filter(pk__in=danger_mother_ids).count()
    stable_count = total_mothers - high_risk_count

    # Observation cases (mothers with some symptoms but not danger)
    observation_ids = set(
        ANCVisit.objects.filter(mother_id__in=volunteer_mother_ids)
        .exclude(symptoms=[])
        .exclude(has_danger_signs=True)
        .values_list("mother_id", flat=True)
    )
    observation_count = len(observation_ids - danger_mother_ids)
    stable_count -= observation_count

    # Weekly registrations (for bar chart)
    weekly_registrations = defaultdict(int)
    for m in all_mothers.filter(
        created_at__date__gte=month_start,
        created_at__date__lte=month_end,
    ):
        week_num = (m.created_at.day - 1) // 7 + 1
        weekly_registrations[f"week{week_num}"] += 1

    # Fill in missing weeks
    for i in range(1, 5):
        weekly_registrations.setdefault(f"week{i}", 0)

    # Calculate percentages for chart
    max_weekly = max(weekly_registrations.values()) if weekly_registrations.values() else 1
    weekly_chart_data = [
        {
            "week": f"W{i}",
            "count": weekly_registrations.get(f"week{i}", 0),
            "percentage": int((weekly_registrations.get(f"week{i}", 0) / max_weekly) * 100) if max_weekly > 0 else 0,
        }
        for i in range(1, 5)
    ]

    # Risk distribution percentages
    total_for_dist = total_mothers or 1
    stable_pct = int((stable_count / total_for_dist) * 100)
    observation_pct = int((observation_count / total_for_dist) * 100)
    high_risk_pct = int((high_risk_count / total_for_dist) * 100)
    risk_distribution = {
        "stable_pct": stable_pct,
        "observation_pct": observation_pct,
        "high_risk_pct": high_risk_pct,
        "stable_plus_obs_pct": stable_pct + observation_pct,
    }

    # Goal progress
    visit_target = 50
    goal_progress = min(100, int((total_anc_visits / visit_target) * 100)) if visit_target > 0 else 0

    # Generate previous months for tabs
    months_list = []
    for i in range(3):
        m = current_month - i
        y = current_year
        if m <= 0:
            m += 12
            y -= 1
        months_list.append({"month": m, "year": y, "is_current": i == 0})

    context = {
        "total_mothers": total_mothers,
        "new_registrations": new_registrations,
        "total_anc_visits": total_anc_visits,
        "high_risk_count": high_risk_count,
        "stable_count": stable_count,
        "observation_count": observation_count,
        "weekly_chart_data": weekly_chart_data,
        "risk_distribution": risk_distribution,
        "goal_progress": goal_progress,
        "visit_target": visit_target,
        "completed_visits": total_anc_visits,
        "months_list": months_list,
        "current_month": current_month,
        "current_year": current_year,
        "current_month_label": date(current_year, current_month, 1).strftime("%B %Y"),
        "total_cases": total_mothers,
        "sos_count": Alert.objects.filter(
            alert_type=Alert.AlertType.EMERGENCY_SOS,
            created_at__year=current_year,
            created_at__month=current_month,
            mother_id__in=MotherProfile.objects.filter(
                registered_by=request.user
            ).values_list("pk", flat=True),
        ).count(),
    }
    return render(request, "mother/monthly_reports.html", context)


# ── Priority Alerts View ────────────────────────────────────────


@login_required
def priority_alerts(request):
    """Display emergency SOS, high-risk monitoring, and missed appointments."""
    filter_type = request.GET.get("filter", "all")

    # Scope everything to this volunteer's mothers
    volunteer_mother_ids = MotherProfile.objects.filter(
        registration_completed=True, registered_by=request.user
    ).values_list("pk", flat=True)

    # Build queryset based on filter
    alerts_qs = Alert.objects.select_related("mother").filter(
        is_resolved=False,
        mother_id__in=volunteer_mother_ids,
    )

    if filter_type == "emergency":
        alerts_qs = alerts_qs.filter(alert_type=Alert.AlertType.EMERGENCY_SOS)
    elif filter_type == "high_risk":
        alerts_qs = alerts_qs.filter(alert_type=Alert.AlertType.HIGH_RISK)
    elif filter_type == "missed":
        alerts_qs = alerts_qs.filter(alert_type=Alert.AlertType.MISSED_VISIT)

    # Emergency SOS alerts (most recent critical, scoped)
    emergency_alert = (
        Alert.objects.filter(
            alert_type=Alert.AlertType.EMERGENCY_SOS,
            is_resolved=False,
            mother_id__in=volunteer_mother_ids,
        )
        .select_related("mother")
        .order_by("-created_at")
        .first()
    )

    # High-risk mother alerts (scoped to this volunteer's mothers)
    high_risk_alerts = []
    danger_mother_ids = set(
        ANCVisit.objects.filter(has_danger_signs=True, mother_id__in=volunteer_mother_ids)
        .values_list("mother_id", flat=True)
    )

    high_risk_mothers = (
        MotherProfile.objects.filter(pk__in=danger_mother_ids)
        .order_by("-updated_at")[:5]
    )
    
    for m in high_risk_mothers:
        latest_visit = m.anc_visits.order_by("-created_at").first()
        weeks = _pregnancy_weeks(m)
        symptoms_display = []
        if latest_visit and latest_visit.symptoms:
            for s in latest_visit.symptoms[:2]:
                symptoms_display.append(s.upper().replace("_", " "))
        
        high_risk_alerts.append({
            "mother": m,
            "initials": _get_initials(m.full_name),
            "weeks": weeks,
            "symptoms": symptoms_display,
            "blood_pressure": latest_visit.blood_pressure if latest_visit else "",
            "time_ago": _time_ago(latest_visit.created_at) if latest_visit else "",
        })

    # Missed appointments (scoped to this volunteer's mothers)
    today = date.today()
    missed_visits = (
        ScheduledVisit.objects.filter(
            scheduled_date__lt=today,
            is_completed=False,
            mother_id__in=volunteer_mother_ids,
        )
        .select_related("mother")
        .order_by("-scheduled_date")[:5]
    )

    missed_appointments = []
    for sv in missed_visits:
        days_ago = (today - sv.scheduled_date).days
        if days_ago == 1:
            time_str = "Yesterday"
        else:
            time_str = f"{days_ago} days ago"
        
        missed_appointments.append({
            "mother": sv.mother,
            "initials": _get_initials(sv.mother.full_name),
            "visit_type": sv.get_visit_type_display(),
            "visit_number": sv.visit_number,
            "scheduled_ago": time_str,
        })

    # Alert counts (scoped to this volunteer's mothers)
    total_alerts = alerts_qs.count()
    emergency_count = Alert.objects.filter(
        alert_type=Alert.AlertType.EMERGENCY_SOS,
        is_resolved=False,
        mother_id__in=volunteer_mother_ids,
    ).count()
    high_risk_count = len(danger_mother_ids)
    missed_count = ScheduledVisit.objects.filter(
        scheduled_date__lt=today,
        is_completed=False,
        mother_id__in=volunteer_mother_ids,
    ).count()

    context = {
        "emergency_alert": emergency_alert,
        "high_risk_alerts": high_risk_alerts,
        "missed_appointments": missed_appointments,
        "total_alerts": total_alerts,
        "emergency_count": emergency_count,
        "high_risk_count": high_risk_count,
        "missed_count": missed_count,
        "filter_type": filter_type,
    }
    return render(request, "mother/prioroty_alerts.html", context)


def _time_ago(dt):
    """Return human-readable time difference."""
    if not dt:
        return ""
    now = timezone.now()
    diff = now - dt
    
    if diff.days > 0:
        return f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
    
    hours = diff.seconds // 3600
    if hours > 0:
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    
    minutes = diff.seconds // 60
    if minutes > 0:
        return f"{minutes} min{'s' if minutes > 1 else ''} ago"
    
    return "Just now"


# ── Records Detail View ─────────────────────────────────────────


@login_required
def records_detail(request):
    """Detailed mother records with search, filter, and pagination."""
    mothers = MotherProfile.objects.filter(
        registration_completed=True,
        registered_by=request.user,
    )

    # Search
    q = request.GET.get("q", "").strip()
    if q:
        mothers = mothers.filter(
            Q(full_name__icontains=q)
            | Q(ward__icontains=q)
            | Q(phone__icontains=q)
        )

    # Risk filter
    risk_filter = request.GET.get("risk", "all")

    # Scope danger/observation to this volunteer's mothers
    volunteer_mother_ids = mothers.values_list("pk", flat=True)
    danger_mother_ids = set(
        ANCVisit.objects.filter(has_danger_signs=True, mother_id__in=volunteer_mother_ids)
        .values_list("mother_id", flat=True)
    )

    # Observation: has symptoms but not danger
    observation_ids = set(
        ANCVisit.objects.filter(mother_id__in=volunteer_mother_ids)
        .exclude(symptoms=[])
        .exclude(has_danger_signs=True)
        .values_list("mother_id", flat=True)
    ) - danger_mother_ids

    if risk_filter == "high":
        mothers = mothers.filter(pk__in=danger_mother_ids)
    elif risk_filter == "stable":
        mothers = mothers.exclude(
            pk__in=danger_mother_ids | observation_ids
        )
    elif risk_filter == "observation":
        mothers = mothers.filter(pk__in=observation_ids)

    # Build detailed records
    today = date.today()
    records = []
    
    for m in mothers[:20]:  # Limit for performance
        weeks = _pregnancy_weeks(m)
        initials = _get_initials(m.full_name)
        
        # Risk classification
        if m.pk in danger_mother_ids:
            risk = "high"
        elif m.pk in observation_ids:
            risk = "observation"
        else:
            risk = "stable"
        
        # Last visit
        last_visit = m.anc_visits.order_by("-visit_date").first()
        last_visit_info = None
        if last_visit:
            symptoms_text = []
            if last_visit.blood_pressure:
                symptoms_text.append(f"BP: {last_visit.blood_pressure}")
            if last_visit.symptoms:
                symptoms_text.extend(
                    s.replace("_", " ").title() 
                    for s in last_visit.symptoms[:1]
                )
            last_visit_info = {
                "date": last_visit.visit_date,
                "symptoms": " • ".join(symptoms_text) if symptoms_text else "Routine Checkup",
            }
        
        # Upcoming visit
        upcoming = (
            ScheduledVisit.objects.filter(
                mother=m,
                scheduled_date__gte=today,
                is_completed=False,
            )
            .order_by("scheduled_date")
            .first()
        )
        upcoming_info = None
        if upcoming:
            days_until = (upcoming.scheduled_date - today).days
            if days_until == 0:
                time_str = "Today"
            elif days_until == 1:
                time_str = "Tomorrow"
            else:
                time_str = f"In {days_until} days"
            
            upcoming_info = {
                "date": upcoming.scheduled_date,
                "days_until": time_str,
            }
        
        records.append({
            "profile": m,
            "initials": initials,
            "weeks": weeks,
            "risk": risk,
            "age": m.age,
            "last_visit": last_visit_info,
            "upcoming": upcoming_info,
        })

    # Metrics
    high_risk_count = len(danger_mother_ids)

    context = {
        "records": records,
        "search_query": q,
        "risk_filter": risk_filter,
        "high_risk_count": high_risk_count,
        "user": request.user,
    }
    return render(request, "mother/mother_records_detail.html", context)


# ── SOS Views ───────────────────────────────────────────────────


def _compute_risk_level(mother: MotherProfile) -> str:
    """
    Derive a risk-level string from the mother's clinical profile.

    Used by the SOS trigger page to pre-fill risk level and by the
    legacy form-POST trigger_sos view.
    """
    danger_visits = ANCVisit.objects.filter(
        mother=mother, has_danger_signs=True,
    ).count()
    week = mother.pregnancy_week or 0
    age = mother.age or 25

    if danger_visits >= 2:
        return SOSEmergency.RiskLevel.CRITICAL
    if week >= 37 and mother.has_previous_complications:
        return SOSEmergency.RiskLevel.CRITICAL
    if danger_visits >= 1:
        return SOSEmergency.RiskLevel.HIGH
    if (age < 18 or age > 35) and mother.has_previous_complications:
        return SOSEmergency.RiskLevel.HIGH
    if mother.has_previous_complications:
        return SOSEmergency.RiskLevel.MODERATE
    return SOSEmergency.RiskLevel.LOW


@login_required
def sos_trigger_page(request, pk):
    """
    Render the dedicated offline-first SOS trigger page.

    Passes mother details and computed risk level to the template
    which uses the SOS JS module for one-tap triggering.
    """
    if request.user.is_staff:
        mother = get_object_or_404(MotherProfile, pk=pk)
    else:
        mother = get_object_or_404(
            MotherProfile, pk=pk, registered_by=request.user,
        )

    context = {
        "mother": mother,
        "risk_level": _compute_risk_level(mother),
    }
    return render(request, "mother/sos_trigger.html", context)


@login_required
def trigger_sos(request, pk):
    """
    Legacy form-POST SOS trigger (non-JS fallback).

    Creates both an SOSEmergency record and legacy Alert so that
    priority_alerts page continues to work.
    """
    if request.user.is_staff:
        profile = get_object_or_404(MotherProfile, pk=pk)
    else:
        profile = get_object_or_404(MotherProfile, pk=pk, registered_by=request.user)

    if request.method == "POST":
        note = request.POST.get("note", "").strip()
        risk = _compute_risk_level(profile)

        # Create SOSEmergency record
        SOSEmergency.objects.create(
            offline_id=uuid.uuid4(),
            mother=profile,
            triggered_by=request.user,
            risk_level=risk,
            latitude=profile.latitude,
            longitude=profile.longitude,
            note=note or f"SOS triggered by {request.user.get_full_name() or request.user.username}.",
            triggered_at=timezone.now(),
            is_synced=True,
            synced_at=timezone.now(),
        )

        # Also create legacy Alert for backward compatibility
        Alert.objects.create(
            mother=profile,
            alert_type=Alert.AlertType.EMERGENCY_SOS,
            priority=Alert.Priority.CRITICAL,
            title="Emergency SOS Triggered",
            message=note
            or f"SOS triggered by {request.user.get_full_name() or request.user.username} for {profile.full_name}.",
            assigned_to=request.user,
        )
        messages.success(request, f"SOS alert triggered for {profile.full_name}. Emergency services notified.")
        return redirect("main:priority_alerts")

    return redirect("main:mother_profile", pk=pk)


@login_required
def sos_history(request, pk):
    """
    Display the SOS emergency history for a specific mother.

    Shows all SOS records (active + resolved) ordered newest first.
    """
    if request.user.is_staff:
        mother = get_object_or_404(MotherProfile, pk=pk)
    else:
        mother = get_object_or_404(
            MotherProfile, pk=pk, registered_by=request.user,
        )

    emergencies = (
        SOSEmergency.objects
        .filter(mother=mother)
        .select_related("triggered_by", "resolved_by")
        .order_by("-triggered_at")
    )

    context = {
        "mother": mother,
        "emergencies": emergencies,
        "active_count": emergencies.filter(
            status__in=[SOSEmergency.Status.ACTIVE, SOSEmergency.Status.RESPONDING],
        ).count(),
    }
    return render(request, "mother/sos_history.html", context)


@login_required
def resolve_alert(request, pk):
    """Mark an alert as resolved."""
    alert = get_object_or_404(Alert, pk=pk)

    # Only the assigned volunteer or admin or the mother's volunteer can resolve
    can_resolve = request.user.is_staff or alert.assigned_to == request.user
    if not can_resolve and alert.mother:
        can_resolve = alert.mother.registered_by == request.user

    if not can_resolve:
        messages.error(request, "You don't have permission to resolve this alert.")
        return redirect("main:priority_alerts")

    if request.method == "POST":
        alert.is_resolved = True
        alert.save(update_fields=["is_resolved"])
        messages.success(request, "Alert marked as resolved.")

    return redirect("main:priority_alerts")