"""
mother/application/commands.py

Write-side command services (use cases) for the Maternal Health bounded context.

Each class represents a single use case.  Commands mutate state — they call the
domain layer and persist changes through the ORM.  Return values are minimal
(the created/updated entity or a simple result object).
"""

from __future__ import annotations

import logging
import uuid
from datetime import date

from django.utils import timezone

from accounts.models import MotherProfile
from mother.domain.services import SOSRiskEvaluator
from mother.models import ANCVisit, Alert, AwarenessProgram, HospitalConsultation, SOSEmergency

logger = logging.getLogger(__name__)


# ── Mother registration ──────────────────────────────────────────


class RegisterMotherCommand:
    """
    Use case: register a new pregnant mother.

    The view hands validated form data to this command; the command
    applies domain defaults and persists the record.
    """

    def execute(self, *, form, registered_by) -> MotherProfile:
        """
        Save the mother profile and mark registration as complete.

        Args:
            form:           A validated MotherRegistrationForm instance.
            registered_by:  The User who is registering the mother.

        Returns:
            The newly saved MotherProfile instance.
        """
        profile: MotherProfile = form.save(commit=False)
        profile.registered_by = registered_by
        profile.registration_completed = True
        profile.save()
        logger.info(
            "Mother '%s' (pk=%s) registered by user '%s'.",
            profile.full_name,
            profile.pk,
            registered_by.username,
        )
        return profile


# ── ANC Visit recording ──────────────────────────────────────────


class RecordANCVisitCommand:
    """
    Use case: record a new Antenatal Care visit for a mother.

    Automatically determines the next visit number.
    """

    def execute(self, *, form, profile: MotherProfile, recorded_by) -> ANCVisit:
        """
        Persist a new ANC visit record.

        Args:
            form:        A validated ANCVisitForm instance.
            profile:     The MotherProfile the visit belongs to.
            recorded_by: The User recording the visit.

        Returns:
            The newly saved ANCVisit instance.
        """
        last_visit = profile.anc_visits.order_by("-visit_number").first()
        next_number = (last_visit.visit_number + 1) if last_visit else 1

        visit: ANCVisit = form.save(commit=False)
        visit.mother = profile
        visit.visit_number = next_number
        visit.recorded_by = recorded_by
        visit.save()

        logger.info(
            "ANC Visit #%d recorded for mother '%s' (pk=%s) by user '%s'.",
            next_number,
            profile.full_name,
            profile.pk,
            recorded_by.username,
        )
        return visit


# ── Hospital Consultation referral ───────────────────────────────


class CreateConsultationCommand:
    """Use case: create a hospital consultation / referral record."""

    @staticmethod
    def _generate_reference_id() -> str:
        return f"CT-{uuid.uuid4().hex[:5].upper()}-X"

    def execute(
        self,
        *,
        form,
        profile: MotherProfile,
        referred_by,
    ) -> HospitalConsultation:
        """
        Persist a new consultation referral.

        Args:
            form:        A validated HospitalConsultationForm instance.
            profile:     The MotherProfile being referred.
            referred_by: The User creating the referral.

        Returns:
            The newly saved HospitalConsultation instance.
        """
        consultation: HospitalConsultation = form.save(commit=False)
        consultation.mother = profile
        consultation.referred_by = referred_by
        consultation.reference_id = self._generate_reference_id()
        consultation.is_synced = True
        consultation.save()

        logger.info(
            "Consultation '%s' created for mother '%s' by user '%s'.",
            consultation.reference_id,
            profile.full_name,
            referred_by.username,
        )
        return consultation


# ── Awareness Program creation ───────────────────────────────────


class CreateAwarenessProgramCommand:
    """Use case: create a community awareness / education event."""

    def execute(
        self,
        *,
        form,
        created_by,
        attendee_ids: list,
    ) -> AwarenessProgram:
        """
        Persist a new awareness program and attach attendees.

        Args:
            form:         A validated AwarenessProgramForm instance.
            created_by:   The User creating the event.
            attendee_ids: List of MotherProfile PKs to attach as attendees.

        Returns:
            The newly saved AwarenessProgram instance.
        """
        program: AwarenessProgram = form.save(commit=False)
        program.created_by = created_by
        program.save()

        if attendee_ids:
            program.attendees.set(attendee_ids)

        logger.info(
            "Awareness program '%s' created by user '%s' with %d attendees.",
            program.get_topic_display(),
            created_by.username,
            len(attendee_ids),
        )
        return program


# ── SOS Emergency ────────────────────────────────────────────────


class TriggerSOSCommand:
    """
    Use case: trigger an SOS emergency alert for a mother.

    Creates both an SOSEmergency record (for the dedicated SOS page)
    and a legacy Alert (for the priority-alerts page).  The risk level
    is computed by the SOSRiskEvaluator domain service.
    """

    def execute(
        self,
        *,
        profile: MotherProfile,
        triggered_by,
        note: str = "",
    ) -> tuple[SOSEmergency, Alert]:
        """
        Create the emergency records.

        Args:
            profile:      The MotherProfile in danger.
            triggered_by: The User who pressed the SOS button.
            note:         Optional free-text description.

        Returns:
            A (SOSEmergency, Alert) tuple.
        """
        danger_count = ANCVisit.objects.filter(
            mother=profile, has_danger_signs=True
        ).count()

        risk_level = SOSRiskEvaluator.evaluate(
            danger_visit_count=danger_count,
            pregnancy_week=profile.pregnancy_week,
            age=profile.age,
            has_previous_complications=profile.has_previous_complications,
        )

        now = timezone.now()
        default_note = (
            note
            or f"SOS triggered by {triggered_by.get_full_name() or triggered_by.username}."
        )

        sos = SOSEmergency.objects.create(
            offline_id=uuid.uuid4(),
            mother=profile,
            triggered_by=triggered_by,
            risk_level=risk_level,
            latitude=profile.latitude,
            longitude=profile.longitude,
            note=default_note,
            triggered_at=now,
            is_synced=True,
            synced_at=now,
        )

        alert = Alert.objects.create(
            mother=profile,
            alert_type=Alert.AlertType.EMERGENCY_SOS,
            priority=Alert.Priority.CRITICAL,
            title="Emergency SOS Triggered",
            message=default_note,
            assigned_to=triggered_by,
        )

        logger.warning(
            "SOS triggered for mother '%s' (pk=%s) by user '%s'. Risk: %s.",
            profile.full_name,
            profile.pk,
            triggered_by.username,
            risk_level.upper(),
        )
        return sos, alert


class ResolveAlertCommand:
    """Use case: mark an alert as resolved."""

    def execute(self, *, alert: Alert, resolved_by) -> Alert:
        """
        Mark the alert resolved and return the updated instance.

        Raises PermissionError if the user is not authorised.
        """
        can_resolve = (
            resolved_by.is_staff
            or alert.assigned_to == resolved_by
            or (alert.mother and alert.mother.registered_by == resolved_by)
        )
        if not can_resolve:
            raise PermissionError("You don't have permission to resolve this alert.")

        alert.is_resolved = True
        alert.save(update_fields=["is_resolved"])
        logger.info(
            "Alert pk=%s resolved by user '%s'.", alert.pk, resolved_by.username
        )
        return alert


# ── Photo update ─────────────────────────────────────────────────

class UpdateMotherPhotoCommand:
    """Use case: replace a mother's profile photo."""

    def execute(self, *, profile: MotherProfile, new_photo) -> MotherProfile:
        """
        Delete the old photo (if any) and save the new one.

        Args:
            profile:   The MotherProfile to update.
            new_photo: The InMemoryUploadedFile from request.FILES.

        Returns:
            The updated MotherProfile instance.
        """
        if profile.photo:
            profile.photo.delete(save=False)
        profile.photo = new_photo
        profile.save(update_fields=["photo"])
        logger.info("Photo updated for mother '%s' (pk=%s).", profile.full_name, profile.pk)
        return profile
