import uuid
from datetime import date, timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db.models import Q, Count
from django.shortcuts import render, redirect, get_object_or_404

from accounts.models import MotherProfile, User
from .forms import ANCVisitForm, AwarenessProgramForm, HospitalConsultationForm
from .models import ANCVisit, AwarenessProgram, HospitalConsultation


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
    mothers = MotherProfile.objects.filter(registration_completed=True)
    total_mothers = mothers.count()

    # High-risk: mothers who have had any ANC visit with danger signs
    high_risk_ids = (
        ANCVisit.objects.filter(has_danger_signs=True)
        .values_list("mother_id", flat=True)
        .distinct()
    )
    high_risk_count = mothers.filter(pk__in=high_risk_ids).count()

    # Upcoming ANC visits — show the most recent visits as a proxy
    recent_visits = (
        ANCVisit.objects.select_related("mother")
        .order_by("-created_at")[:5]
    )

    # Monthly goal progress (simple: percentage of mothers with ≥1 visit)
    mothers_with_visits = (
        ANCVisit.objects.values("mother_id").distinct().count()
    )
    goal_progress = (
        int((mothers_with_visits / total_mothers) * 100)
        if total_mothers > 0
        else 0
    )

    context = {
        "total_mothers": total_mothers,
        "high_risk_count": high_risk_count,
        "recent_visits": recent_visits,
        "goal_progress": goal_progress,
        "user": request.user,
    }
    return render(request, "mother/dashboard.html", context)


# ── Mother List ─────────────────────────────────────────────────


@login_required
def mother_list(request):
    """List all registered mothers with search & risk-filter support."""
    mothers = MotherProfile.objects.filter(registration_completed=True).select_related("user")

    # Search
    q = request.GET.get("q", "").strip()
    if q:
        mothers = mothers.filter(
            Q(full_name__icontains=q)
            | Q(ward__icontains=q)
            | Q(user__phone__icontains=q)
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
    profile = get_object_or_404(MotherProfile, pk=pk)

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
    profile = get_object_or_404(MotherProfile, pk=pk)

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
    mothers = MotherProfile.objects.filter(registration_completed=True)

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
    profile = get_object_or_404(MotherProfile, pk=pk)
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

