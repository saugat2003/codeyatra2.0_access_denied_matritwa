"""
mother/application/queries.py

Read-side query services for the Maternal Health bounded context.

Query services are responsible for assembling the data needed for a
particular UI view.  They coordinate the domain layer and ORM queries,
returning plain Python data structures (dicts / dataclasses) so views
stay thin.

No business logic should live here; delegate to domain/services.py.
"""

from __future__ import annotations

import logging
from collections import defaultdict
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import Optional

from django.db.models import Count, Q

from accounts.models import MotherProfile
from mother.domain.services import (
    PregnancyCalculator,
    RiskClassifier,
    TimeAgoFormatter,
)
from mother.domain.value_objects import Initials
from mother.models import ANCVisit, Alert, ScheduledVisit

logger = logging.getLogger(__name__)


# ── Shared helpers ───────────────────────────────────────────────


def _get_volunteer_mother_ids(user):
    """Return a queryset of PKs for all completed mothers registered by *user*."""
    return MotherProfile.objects.filter(
        registration_completed=True,
        registered_by=user,
    ).values_list("pk", flat=True)


def _build_danger_ids(volunteer_mother_ids) -> set:
    """Set of mother PKs that have ≥1 ANC visit with danger signs."""
    return set(
        ANCVisit.objects.filter(
            has_danger_signs=True,
            mother_id__in=volunteer_mother_ids,
        ).values_list("mother_id", flat=True)
    )


def _build_observation_ids(volunteer_mother_ids, danger_ids: set) -> set:
    """Set of mother PKs with symptoms but no danger signs."""
    return (
        set(
            ANCVisit.objects.filter(mother_id__in=volunteer_mother_ids)
            .exclude(symptoms=[])
            .exclude(has_danger_signs=True)
            .values_list("mother_id", flat=True)
        )
        - danger_ids
    )


# ── Data transfer objects (DTOs) ─────────────────────────────────


@dataclass
class MotherSummaryDTO:
    """Lightweight summary used by dashboard and mother-list views."""

    profile: MotherProfile
    initials: str
    weeks: Optional[int]
    risk: str
    visit_count: int = 0


@dataclass
class MotherRecordDTO:
    """Richer record used by the records-detail view."""

    profile: MotherProfile
    initials: str
    weeks: Optional[int]
    risk: str
    age: Optional[int]
    last_visit: Optional[dict]
    upcoming: Optional[dict]


@dataclass
class DashboardStats:
    """All statistics needed for the FCHV dashboard."""

    total_mothers: int
    high_risk_count: int
    goal_progress: int
    recent_visits: list
    active_mothers: list[MotherSummaryDTO]


@dataclass
class MonthlyReportData:
    """All data needed to render the monthly reports page."""

    total_mothers: int
    new_registrations: int
    total_anc_visits: int
    high_risk_count: int
    stable_count: int
    observation_count: int
    weekly_chart_data: list
    risk_distribution: dict
    goal_progress: int
    visit_target: int
    sos_count: int
    months_list: list
    current_month: int
    current_year: int
    current_month_label: str


@dataclass
class AlertsData:
    """All data needed to render the priority alerts page."""

    emergency_alert: Optional[object]
    high_risk_alerts: list
    missed_appointments: list
    total_alerts: int
    emergency_count: int
    high_risk_count: int
    missed_count: int
    filter_type: str


# ── Query services ───────────────────────────────────────────────


class DashboardQueryService:
    """Assembles all data required by the FCHV dashboard view."""

    def get_dashboard_stats(self, user) -> DashboardStats:
        mothers = MotherProfile.objects.filter(
            registration_completed=True,
            registered_by=user,
        )
        total_mothers = mothers.count()
        volunteer_mother_ids = mothers.values_list("pk", flat=True)

        danger_ids = _build_danger_ids(volunteer_mother_ids)
        high_risk_count = mothers.filter(pk__in=danger_ids).count()

        recent_visits = (
            ANCVisit.objects.filter(mother_id__in=volunteer_mother_ids)
            .select_related("mother")
            .order_by("-created_at")[:5]
        )

        mothers_with_visits = (
            ANCVisit.objects.filter(mother_id__in=volunteer_mother_ids)
            .values("mother_id")
            .distinct()
            .count()
        )
        goal_progress = (
            int((mothers_with_visits / total_mothers) * 100)
            if total_mothers > 0
            else 0
        )

        recent_mothers = mothers.order_by("-created_at")[:5]
        active_mothers = [
            MotherSummaryDTO(
                profile=m,
                initials=str(Initials.from_name(m.full_name)),
                weeks=self._get_weeks(m),
                risk="high" if m.pk in danger_ids else "stable",
            )
            for m in recent_mothers
        ]

        return DashboardStats(
            total_mothers=total_mothers,
            high_risk_count=high_risk_count,
            goal_progress=goal_progress,
            recent_visits=list(recent_visits),
            active_mothers=active_mothers,
        )

    @staticmethod
    def _get_weeks(mother) -> Optional[int]:
        pw = PregnancyCalculator.get_pregnancy_week(mother.lmp_date, mother.pregnancy_week)
        return pw.value if pw else None


class MotherListQueryService:
    """Assembles the filtered + annotated mother list."""

    def get_mother_list(self, user, search_query: str = "", risk_filter: str = "") -> list[MotherSummaryDTO]:
        mothers = MotherProfile.objects.filter(
            registration_completed=True,
            registered_by=user,
        )

        if search_query:
            mothers = mothers.filter(
                Q(full_name__icontains=search_query)
                | Q(ward__icontains=search_query)
                | Q(phone__icontains=search_query)
            )

        volunteer_mother_ids = mothers.values_list("pk", flat=True)
        danger_ids = _build_danger_ids(volunteer_mother_ids)

        if risk_filter == "high":
            mothers = mothers.filter(pk__in=danger_ids)
        elif risk_filter == "stable":
            mothers = mothers.exclude(pk__in=danger_ids)

        mothers = mothers.annotate(visit_count=Count("anc_visits"))

        result = []
        for m in mothers:
            pw = PregnancyCalculator.get_pregnancy_week(m.lmp_date, m.pregnancy_week)
            risk = RiskClassifier.classify(m.pk, danger_ids, set())
            result.append(
                MotherSummaryDTO(
                    profile=m,
                    initials=str(Initials.from_name(m.full_name)),
                    weeks=pw.value if pw else None,
                    risk=str(risk),
                    visit_count=m.visit_count,
                )
            )
        return result


class RecordsDetailQueryService:
    """Assembles the detailed mother records with risk classification."""

    LIMIT = 20  # Performance cap

    def get_records(self, user, search_query: str = "", risk_filter: str = "all") -> list[MotherRecordDTO]:
        mothers = MotherProfile.objects.filter(
            registration_completed=True,
            registered_by=user,
        )

        if search_query:
            mothers = mothers.filter(
                Q(full_name__icontains=search_query)
                | Q(ward__icontains=search_query)
                | Q(phone__icontains=search_query)
            )

        volunteer_mother_ids = mothers.values_list("pk", flat=True)
        danger_ids = _build_danger_ids(volunteer_mother_ids)
        observation_ids = _build_observation_ids(volunteer_mother_ids, danger_ids)

        if risk_filter == "high":
            mothers = mothers.filter(pk__in=danger_ids)
        elif risk_filter == "stable":
            mothers = mothers.exclude(pk__in=danger_ids | observation_ids)
        elif risk_filter == "observation":
            mothers = mothers.filter(pk__in=observation_ids)

        today = date.today()
        records = []

        for m in mothers[: self.LIMIT]:
            pw = PregnancyCalculator.get_pregnancy_week(m.lmp_date, m.pregnancy_week)
            risk = RiskClassifier.classify(m.pk, danger_ids, observation_ids)

            last_visit = m.anc_visits.order_by("-visit_date").first()
            last_visit_info = self._build_last_visit_info(last_visit)
            upcoming_info = self._build_upcoming_info(m, today)

            records.append(
                MotherRecordDTO(
                    profile=m,
                    initials=str(Initials.from_name(m.full_name)),
                    weeks=pw.value if pw else None,
                    risk=str(risk),
                    age=m.age,
                    last_visit=last_visit_info,
                    upcoming=upcoming_info,
                )
            )
        return records

    @staticmethod
    def _build_last_visit_info(last_visit) -> Optional[dict]:
        if not last_visit:
            return None
        parts = []
        if last_visit.blood_pressure:
            parts.append(f"BP: {last_visit.blood_pressure}")
        if last_visit.symptoms:
            parts.extend(s.replace("_", " ").title() for s in last_visit.symptoms[:1])
        return {
            "date": last_visit.visit_date,
            "symptoms": " • ".join(parts) if parts else "Routine Checkup",
        }

    @staticmethod
    def _build_upcoming_info(mother, today: date) -> Optional[dict]:
        upcoming = (
            ScheduledVisit.objects.filter(
                mother=mother,
                scheduled_date__gte=today,
                is_completed=False,
            )
            .order_by("scheduled_date")
            .first()
        )
        if not upcoming:
            return None
        days = (upcoming.scheduled_date - today).days
        if days == 0:
            time_str = "Today"
        elif days == 1:
            time_str = "Tomorrow"
        else:
            time_str = f"In {days} days"
        return {"date": upcoming.scheduled_date, "days_until": time_str}


class MonthlyReportQueryService:
    """Assembles all data for the monthly performance report."""

    VISIT_TARGET = 50

    def get_report(self, user, month: int, year: int) -> MonthlyReportData:
        month_start = date(year, month, 1)
        if month == 12:
            month_end = date(year + 1, 1, 1) - timedelta(days=1)
        else:
            month_end = date(year, month + 1, 1) - timedelta(days=1)

        all_mothers = MotherProfile.objects.filter(
            registration_completed=True, registered_by=user
        )
        total_mothers = all_mothers.count()
        volunteer_mother_ids = all_mothers.values_list("pk", flat=True)

        new_registrations = all_mothers.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end,
        ).count()

        month_visits = ANCVisit.objects.filter(
            mother_id__in=volunteer_mother_ids,
            visit_date__gte=month_start,
            visit_date__lte=month_end,
        )
        total_anc_visits = month_visits.count()

        danger_ids = _build_danger_ids(volunteer_mother_ids)
        high_risk_count = all_mothers.filter(pk__in=danger_ids).count()
        observation_ids = _build_observation_ids(volunteer_mother_ids, danger_ids)
        observation_count = len(observation_ids)
        stable_count = max(0, total_mothers - high_risk_count - observation_count)

        weekly_registrations = defaultdict(int)
        for m in all_mothers.filter(
            created_at__date__gte=month_start,
            created_at__date__lte=month_end,
        ):
            week_num = (m.created_at.day - 1) // 7 + 1
            weekly_registrations[f"week{week_num}"] += 1
        for i in range(1, 5):
            weekly_registrations.setdefault(f"week{i}", 0)

        max_weekly = max(weekly_registrations.values()) or 1
        weekly_chart_data = [
            {
                "week": f"W{i}",
                "count": weekly_registrations.get(f"week{i}", 0),
                "percentage": int(
                    (weekly_registrations.get(f"week{i}", 0) / max_weekly) * 100
                )
                if max_weekly > 0
                else 0,
            }
            for i in range(1, 5)
        ]

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

        goal_progress = (
            min(100, int((total_anc_visits / self.VISIT_TARGET) * 100))
            if self.VISIT_TARGET > 0
            else 0
        )

        sos_count = Alert.objects.filter(
            alert_type=Alert.AlertType.EMERGENCY_SOS,
            created_at__year=year,
            created_at__month=month,
            mother_id__in=volunteer_mother_ids,
        ).count()

        months_list = []
        for i in range(3):
            m_val = month - i
            y_val = year
            if m_val <= 0:
                m_val += 12
                y_val -= 1
            months_list.append({"month": m_val, "year": y_val, "is_current": i == 0})

        return MonthlyReportData(
            total_mothers=total_mothers,
            new_registrations=new_registrations,
            total_anc_visits=total_anc_visits,
            high_risk_count=high_risk_count,
            stable_count=stable_count,
            observation_count=observation_count,
            weekly_chart_data=weekly_chart_data,
            risk_distribution=risk_distribution,
            goal_progress=goal_progress,
            visit_target=self.VISIT_TARGET,
            sos_count=sos_count,
            months_list=months_list,
            current_month=month,
            current_year=year,
            current_month_label=date(year, month, 1).strftime("%B %Y"),
        )


class AlertsQueryService:
    """Assembles all data needed by the priority-alerts view."""

    def get_alerts_data(self, user, filter_type: str = "all") -> AlertsData:
        volunteer_mother_ids = _get_volunteer_mother_ids(user)

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

        danger_ids = _build_danger_ids(volunteer_mother_ids)
        high_risk_mothers = (
            MotherProfile.objects.filter(pk__in=danger_ids)
            .order_by("-updated_at")[:5]
        )

        high_risk_alerts = []
        for m in high_risk_mothers:
            latest_visit = m.anc_visits.order_by("-created_at").first()
            pw = PregnancyCalculator.get_pregnancy_week(m.lmp_date, m.pregnancy_week)
            symptoms_display = []
            if latest_visit and latest_visit.symptoms:
                symptoms_display = [
                    s.upper().replace("_", " ") for s in latest_visit.symptoms[:2]
                ]
            high_risk_alerts.append({
                "mother": m,
                "initials": str(Initials.from_name(m.full_name)),
                "weeks": pw.value if pw else None,
                "symptoms": symptoms_display,
                "blood_pressure": latest_visit.blood_pressure if latest_visit else "",
                "time_ago": TimeAgoFormatter.format(latest_visit.created_at) if latest_visit else "",
            })

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
            time_str = "Yesterday" if days_ago == 1 else f"{days_ago} days ago"
            missed_appointments.append({
                "mother": sv.mother,
                "initials": str(Initials.from_name(sv.mother.full_name)),
                "visit_type": sv.get_visit_type_display(),
                "visit_number": sv.visit_number,
                "scheduled_ago": time_str,
            })

        return AlertsData(
            emergency_alert=emergency_alert,
            high_risk_alerts=high_risk_alerts,
            missed_appointments=missed_appointments,
            total_alerts=alerts_qs.count(),
            emergency_count=Alert.objects.filter(
                alert_type=Alert.AlertType.EMERGENCY_SOS,
                is_resolved=False,
                mother_id__in=volunteer_mother_ids,
            ).count(),
            high_risk_count=len(danger_ids),
            missed_count=ScheduledVisit.objects.filter(
                scheduled_date__lt=today,
                is_completed=False,
                mother_id__in=volunteer_mother_ids,
            ).count(),
            filter_type=filter_type,
        )
