"""
healthcare/views.py — Thin HTTP adapter for the Healthcare Analytics bounded context.
"""

import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .services import HealthcareDashboardQueryService

logger = logging.getLogger(__name__)

_dashboard_service = HealthcareDashboardQueryService()


@login_required
def dashboard(request):
    """Healthcare worker dashboard with aggregate statistics."""
    data = _dashboard_service.get_dashboard_data(request.user)

    context = {
        "total_mothers": data.total_mothers,
        "high_risk_count": data.high_risk_count,
        "total_visits": data.total_visits,
        "total_consultations": data.total_consultations,
        "total_programs": data.total_programs,
        "danger_visits": data.danger_visits,
        "recent_consultations": data.recent_consultations,
    }
    return render(request, "healthcare/dashboard.html", context)
