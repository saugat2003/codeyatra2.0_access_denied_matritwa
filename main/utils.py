"""Utility functions for the main app."""

from datetime import date, timedelta


def get_pregnancy_week(lmp_date: date) -> int:
    """Calculate current pregnancy week from Last Menstrual Period date."""
    if not lmp_date:
        return 0
    days = (date.today() - lmp_date).days
    week = days // 7
    return max(0, min(week, 42))  # cap at 42 weeks


def get_trimester(week: int) -> int:
    """Return trimester number (1-3) from pregnancy week."""
    if week <= 12:
        return 1
    if week <= 27:
        return 2
    return 3


def get_expected_delivery_date(lmp_date: date) -> date:
    """Naegele's rule: EDD = LMP + 280 days."""
    if not lmp_date:
        return None
    return lmp_date + timedelta(days=280)


def get_days_remaining(edd: date) -> int:
    """Days remaining until expected delivery."""
    if not edd:
        return 0
    remaining = (edd - date.today()).days
    return max(0, remaining)


def get_pregnancy_progress_percent(week: int) -> float:
    """Return pregnancy progress as a percentage (0-100)."""
    return min(round((week / 40) * 100, 1), 100)


def get_streak_count(streaks_qs) -> int:
    """
    Calculate consecutive days streak from a queryset of HealthStreak objects
    ordered by -date.
    """
    count = 0
    expected = date.today()
    for streak in streaks_qs.order_by("-date"):
        if streak.date == expected and streak.score >= 3:
            count += 1
            expected -= timedelta(days=1)
        else:
            break
    return count
