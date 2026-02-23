"""
mother/domain/services.py

Pure domain services for the Maternal Health bounded context.

Domain services implement business logic that spans multiple entities or
value objects and does NOT naturally belong to a single entity.  There are
NO Django / ORM imports here — only plain Python.
"""

from __future__ import annotations

from datetime import date
from typing import Optional

from .value_objects import EstimatedDueDate, Initials, PregnancyWeek, RiskStatus


class PregnancyCalculator:
    """
    Domain service: all pregnancy-date calculations.

    Centralises Naegele's rule and gestational-week derivation so the
    same logic is never duplicated across views or API handlers.
    """

    @staticmethod
    def get_pregnancy_week(
        lmp_date: Optional[date],
        stored_week: Optional[int],
    ) -> Optional[PregnancyWeek]:
        """
        Return the current gestational week as a value object.

        Preference: calculate from LMP when available (more accurate),
        otherwise fall back to the week stored at registration time.
        """
        if lmp_date:
            return PregnancyWeek.from_lmp(lmp_date)
        if stored_week is not None:
            try:
                return PregnancyWeek(value=stored_week)
            except ValueError:
                return None
        return None

    @staticmethod
    def get_estimated_due_date(
        lmp_date: Optional[date],
        stored_week: Optional[int],
    ) -> Optional[EstimatedDueDate]:
        """
        Return the Estimated Due Date using Naegele's rule when possible,
        or derive from the stored gestational week.
        """
        if lmp_date:
            return EstimatedDueDate.from_lmp(lmp_date)
        if stored_week is not None:
            return EstimatedDueDate.from_pregnancy_week(stored_week)
        return None


class RiskClassifier:
    """
    Domain service: classify a mother's clinical risk level.

    Rules:
      - HIGH       → at least one ANC visit recorded danger signs
      - OBSERVATION → has ANC symptoms but none classed as danger signs
      - STABLE     → no recorded symptoms or no visits yet
    """

    @staticmethod
    def classify(mother_id: int, danger_ids: set, observation_ids: set) -> RiskStatus:
        """
        Classify risk given pre-computed ID sets.

        Callers (repositories or query services) build the sets; this service
        applies the classification rules.

        Args:
            mother_id:        PK of the MotherProfile being classified.
            danger_ids:       Set of mother PKs with confirmed danger signs.
            observation_ids:  Set of mother PKs with symptoms but no danger signs.

        Returns:
            A RiskStatus value object.
        """
        if mother_id in danger_ids:
            return RiskStatus.high()
        if mother_id in observation_ids:
            return RiskStatus.observation()
        return RiskStatus.stable()


class SOSRiskEvaluator:
    """
    Domain service: derive SOSEmergency risk level from a mother's profile.

    This logic is the canonical single source of truth for SOS risk assessment;
    it was previously duplicated in both mother/views.py and mother/api.py.
    """

    @staticmethod
    def evaluate(
        *,
        danger_visit_count: int,
        pregnancy_week: Optional[int],
        age: Optional[int],
        has_previous_complications: bool,
    ) -> str:
        """
        Return a risk-level string matching SOSEmergency.RiskLevel choices.

        Args:
            danger_visit_count:         How many ANC visits recorded danger signs.
            pregnancy_week:             Current gestational week (may be None).
            age:                        Mother's age (may be None; defaults to 25).
            has_previous_complications: Whether previous pregnancy complications exist.

        Returns:
            One of: "critical", "high", "moderate", "low"
        """
        week = pregnancy_week or 0
        effective_age = age or 25

        # Critical: ≥2 danger-sign visits, OR late-term with complications
        if danger_visit_count >= 2:
            return "critical"
        if week >= 37 and has_previous_complications:
            return "critical"

        # High: any danger-sign visit, OR young/older mother with complications
        if danger_visit_count >= 1:
            return "high"
        if (effective_age < 18 or effective_age > 35) and has_previous_complications:
            return "high"

        # Moderate: previous complications only
        if has_previous_complications:
            return "moderate"

        return "low"


class TimeAgoFormatter:
    """
    Domain service: convert a datetime into a human-readable elapsed-time string.

    Centralises the "X minutes/hours/days ago" logic that was previously
    duplicated in model properties, views, and API helpers.
    """

    @staticmethod
    def format(dt, now=None) -> str:
        """
        Return a human-readable string like "5 mins ago", "2 hours ago", etc.

        Args:
            dt:  A timezone-aware datetime to compare.
            now: Reference point (defaults to django.utils.timezone.now()).

        Returns:
            A short string, e.g. "Just now", "3 mins ago", "1 hour ago".
        """
        if dt is None:
            return ""

        if now is None:
            from django.utils import timezone
            now = timezone.now()

        diff = now - dt

        if diff.days > 0:
            n = diff.days
            return f"{n} day{'s' if n > 1 else ''} ago"

        hours = diff.seconds // 3600
        if hours > 0:
            return f"{hours} hour{'s' if hours > 1 else ''} ago"

        minutes = diff.seconds // 60
        if minutes > 0:
            return f"{minutes} min{'s' if minutes > 1 else ''} ago"

        return "Just now"
