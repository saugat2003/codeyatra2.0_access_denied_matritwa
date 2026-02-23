from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render

from accounts.models import MotherProfile
from mother.models import ANCVisit, AwarenessProgram, HospitalConsultation


@login_required
def dashboard(request):
    """Healthcare worker dashboard with aggregate statistics."""
    mothers = MotherProfile.objects.filter(registration_completed=True)
    total_mothers = mothers.count()

    # High-risk count
    high_risk_ids = (
        ANCVisit.objects.filter(has_danger_signs=True)
        .values_list("mother_id", flat=True)
        .distinct()
    )
    high_risk_count = mothers.filter(pk__in=high_risk_ids).count()

    # Total ANC visits
    total_visits = ANCVisit.objects.count()

    # Total consultations
    total_consultations = HospitalConsultation.objects.count()

    # Total awareness programs
    total_programs = AwarenessProgram.objects.count()

    # Recent danger-sign visits
    danger_visits = (
        ANCVisit.objects.filter(has_danger_signs=True)
        .select_related("mother")
        .order_by("-created_at")[:5]
    )

    # Recent consultations
    recent_consultations = (
        HospitalConsultation.objects.select_related("mother")
        .order_by("-created_at")[:5]
    )

    context = {
        "total_mothers": total_mothers,
        "high_risk_count": high_risk_count,
        "total_visits": total_visits,
        "total_consultations": total_consultations,
        "total_programs": total_programs,
        "danger_visits": danger_visits,
        "recent_consultations": recent_consultations,
    }
    return render(request, "healthcare/dashboard.html", context)
