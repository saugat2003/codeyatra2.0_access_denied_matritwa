"""
healthcare/services.py — Application-layer query service for Healthcare Analytics.

Encapsulates all ORM queries for the healthcare dashboard so the view
stays thin and the logic is independently testable.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field

from accounts.models import MotherProfile
from mother.models import ANCVisit, AwarenessProgram, HospitalConsultation

logger = logging.getLogger(__name__)


@dataclass
class HealthcareDashboardData:
    """All statistics needed by the healthcare worker dashboard."""

    total_mothers: int
    high_risk_count: int
    total_visits: int
    total_consultations: int
    total_programs: int
    danger_visits: list
    recent_consultations: list


class HealthcareDashboardQueryService:
    """
    Assembles aggregate statistics for the healthcare worker dashboard.

    Scoped to the requesting user's registered mothers.
    """

    def get_dashboard_data(self, user) -> HealthcareDashboardData:
        mothers = MotherProfile.objects.filter(
            registration_completed=True, registered_by=user
        )
        total_mothers = mothers.count()
        volunteer_mother_ids = mothers.values_list("pk", flat=True)

        high_risk_ids = (
            ANCVisit.objects.filter(
                has_danger_signs=True, mother_id__in=volunteer_mother_ids
            )
            .values_list("mother_id", flat=True)
            .distinct()
        )
        high_risk_count = mothers.filter(pk__in=high_risk_ids).count()

        total_visits = ANCVisit.objects.filter(
            mother_id__in=volunteer_mother_ids
        ).count()

        total_consultations = HospitalConsultation.objects.filter(
            mother_id__in=volunteer_mother_ids
        ).count()

        total_programs = AwarenessProgram.objects.filter(created_by=user).count()

        danger_visits = list(
            ANCVisit.objects.filter(
                has_danger_signs=True, mother_id__in=volunteer_mother_ids
            )
            .select_related("mother")
            .order_by("-created_at")[:5]
        )

        recent_consultations = list(
            HospitalConsultation.objects.filter(mother_id__in=volunteer_mother_ids)
            .select_related("mother")
            .order_by("-created_at")[:5]
        )

        logger.debug(
            "Healthcare dashboard data assembled for user '%s': "
            "%d mothers, %d high-risk.",
            user.username,
            total_mothers,
            high_risk_count,
        )

        return HealthcareDashboardData(
            total_mothers=total_mothers,
            high_risk_count=high_risk_count,
            total_visits=total_visits,
            total_consultations=total_consultations,
            total_programs=total_programs,
            danger_visits=danger_visits,
            recent_consultations=recent_consultations,
        )
