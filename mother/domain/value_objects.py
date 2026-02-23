"""
mother/domain/value_objects.py

Immutable value objects for the Maternal Health domain.

Value objects encapsulate domain concepts that have no identity of their own —
they are equal if all their attributes are equal.  They carry no ORM coupling.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, timedelta
from typing import Optional


@dataclass(frozen=True)
class PregnancyWeek:
    """
    Gestational age expressed in whole weeks.

    Can be calculated from an LMP date or stored directly from intake.
    Weeks are clamped to the clinically meaningful range [1, 42].
    """

    value: int

    def __post_init__(self):
        if not (1 <= self.value <= 42):
            raise ValueError(f"Pregnancy week must be between 1 and 42, got {self.value}.")

    @classmethod
    def from_lmp(cls, lmp_date: date) -> "PregnancyWeek":
        """Calculate gestational week from the Last Menstrual Period date."""
        delta = date.today() - lmp_date
        weeks = max(1, delta.days // 7)
        # Clamp to valid range; beyond 42 is still 42 clinically
        weeks = min(weeks, 42)
        return cls(value=weeks)

    @property
    def trimester(self) -> str:
        """Return human-readable trimester label."""
        if self.value <= 12:
            return "1st Trimester"
        if self.value <= 27:
            return "2nd Trimester"
        return "3rd Trimester"

    def __str__(self) -> str:
        return f"Week {self.value}"


@dataclass(frozen=True)
class EstimatedDueDate:
    """
    Expected Date of Delivery calculated via Naegele's rule (LMP + 280 days)
    or from a known pregnancy week.
    """

    value: date

    @classmethod
    def from_lmp(cls, lmp_date: date) -> "EstimatedDueDate":
        """Naegele's rule: LMP + 280 days."""
        return cls(value=lmp_date + timedelta(days=280))

    @classmethod
    def from_pregnancy_week(cls, week: int) -> "EstimatedDueDate":
        """Estimate EDD from current gestational week."""
        remaining_weeks = 40 - week
        return cls(value=date.today() + timedelta(weeks=remaining_weeks))

    def __str__(self) -> str:
        return self.value.strftime("%B %d, %Y")


@dataclass(frozen=True)
class Initials:
    """
    A person's initials derived from their full name.

    Example: "Sunita Karki" → "SK"
    """

    value: str

    @classmethod
    def from_name(cls, full_name: str) -> "Initials":
        if not full_name or not full_name.strip():
            return cls(value="?")
        parts = full_name.strip().split()
        initials = "".join(w[0].upper() for w in parts[:2] if w)
        return cls(value=initials or "?")

    def __str__(self) -> str:
        return self.value


@dataclass(frozen=True)
class RiskStatus:
    """
    Clinical risk classification for a mother.

    Derived from ANC visit history (danger signs) and symptom records.
    """

    HIGH = "high"
    OBSERVATION = "observation"
    STABLE = "stable"

    level: str

    @classmethod
    def high(cls) -> "RiskStatus":
        return cls(level=cls.HIGH)

    @classmethod
    def observation(cls) -> "RiskStatus":
        return cls(level=cls.OBSERVATION)

    @classmethod
    def stable(cls) -> "RiskStatus":
        return cls(level=cls.STABLE)

    @property
    def is_high(self) -> bool:
        return self.level == self.HIGH

    def __str__(self) -> str:
        return self.level

