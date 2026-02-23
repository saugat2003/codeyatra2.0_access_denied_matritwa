"""
mother/api.py — REST-style JSON API for SOS Emergencies (offline-first).

This module is the HTTP adapter for SOS API operations.
All domain logic is delegated to the application layer (commands) and
the domain service (SOSRiskEvaluator).

Endpoints
─────────
POST  /api/sos/                Create a single SOS emergency
POST  /api/sos/sync/           Bulk-sync queued offline SOS records
GET   /api/sos/active/         List active (unresolved) emergencies
POST  /api/sos/<pk>/resolve/   Resolve an SOS emergency

All responses are JSON.
Authentication: session-based (returns 401 instead of redirecting).
"""

from __future__ import annotations

import json
import logging
import uuid as _uuid
from datetime import datetime
from functools import wraps

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from accounts.models import MotherProfile
from mother.domain.services import SOSRiskEvaluator
from mother.models import Alert, ANCVisit, SOSEmergency

logger = logging.getLogger(__name__)


# ── Auth decorator ────────────────────────────────────────────────


def _api_login_required(view_fn):
    """Return 401 JSON instead of redirecting to the login page."""

    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"ok": False, "error": "Authentication required."},
                status=401,
            )
        return view_fn(request, *args, **kwargs)

    return wrapper


# ── Serialiser ────────────────────────────────────────────────────


def _sos_to_dict(sos: SOSEmergency) -> dict:
    """Serialise an SOSEmergency record to a JSON-friendly dict."""
    return {
        "id": sos.pk,
        "offline_id": str(sos.offline_id),
        "mother_id": sos.mother_id,
        "mother_name": sos.mother.full_name,
        "mother_phone": sos.mother.phone or "",
        "emergency_contact": getattr(sos.mother, "emergency_contact", "") or "",
        "risk_level": sos.risk_level,
        "status": sos.status,
        "latitude": str(sos.latitude) if sos.latitude else None,
        "longitude": str(sos.longitude) if sos.longitude else None,
        "note": sos.note,
        "triggered_at": sos.triggered_at.isoformat(),
        "triggered_by": sos.triggered_by.get_full_name() if sos.triggered_by else "",
        "is_synced": sos.is_synced,
        "time_ago": sos.time_ago,
    }


# ── Infrastructure helper: create or deduplicate an SOS record ────


def _create_or_get_sos(payload: dict, user) -> SOSEmergency:
    """
    Create (or return the existing) SOSEmergency from a request payload.

    Uses the offline_id as a deduplication key so retried offline syncs
    are idempotent.

    Raises:
        ValueError: with a human-readable message on invalid input.
    """
    mother_id = payload.get("mother_id")
    if not mother_id:
        raise ValueError("mother_id is required.")

    try:
        mother = MotherProfile.objects.get(pk=mother_id)
    except MotherProfile.DoesNotExist:
        raise ValueError(f"Mother with id={mother_id} not found.")

    # Parse / generate offline deduplication UUID
    raw_oid = payload.get("offline_id")
    try:
        offline_id = _uuid.UUID(str(raw_oid)) if raw_oid else _uuid.uuid4()
    except (ValueError, AttributeError):
        offline_id = _uuid.uuid4()

    # Idempotency: return existing record if already synced
    existing = SOSEmergency.objects.filter(offline_id=offline_id).first()
    if existing:
        return existing

    # Parse triggered_at timestamp (ISO 8601 from client, or now)
    raw_ts = payload.get("triggered_at")
    try:
        triggered_at = datetime.fromisoformat(raw_ts) if raw_ts else timezone.now()
    except (ValueError, TypeError):
        triggered_at = timezone.now()
    if timezone.is_naive(triggered_at):
        triggered_at = timezone.make_aware(triggered_at)

    # Compute risk using the canonical domain service
    if payload.get("risk_level"):
        risk_level = payload["risk_level"]
    else:
        danger_count = ANCVisit.objects.filter(mother=mother, has_danger_signs=True).count()
        risk_level = SOSRiskEvaluator.evaluate(
            danger_visit_count=danger_count,
            pregnancy_week=mother.pregnancy_week,
            age=mother.age,
            has_previous_complications=mother.has_previous_complications,
        )

    is_synced = payload.get("is_synced", True)

    sos = SOSEmergency.objects.create(
        offline_id=offline_id,
        mother=mother,
        triggered_by=user if user.is_authenticated else None,
        risk_level=risk_level,
        latitude=payload.get("latitude") or mother.latitude,
        longitude=payload.get("longitude") or mother.longitude,
        note=payload.get("note", ""),
        triggered_at=triggered_at,
        is_synced=is_synced,
        synced_at=timezone.now() if is_synced else None,
    )

    # Create the legacy Alert so the priority-alerts view picks it up
    Alert.objects.create(
        mother=mother,
        alert_type=Alert.AlertType.EMERGENCY_SOS,
        priority=Alert.Priority.CRITICAL,
        title=f"SOS — {mother.full_name}",
        message=sos.note or (
            f"Emergency SOS triggered by "
            f"{user.get_full_name() or user.username}."
        ),
        assigned_to=user if user.is_authenticated else None,
    )

    logger.warning(
        "SOS created via API for mother pk=%s (offline_id=%s, risk=%s).",
        mother.pk,
        offline_id,
        risk_level.upper(),
    )
    return sos


# ── API endpoints ─────────────────────────────────────────────────


@csrf_exempt
@require_POST
@_api_login_required
def api_sos_create(request):
    """
    Create a single SOS emergency.

    JSON body keys:
        mother_id    (int)   — required
        offline_id   (uuid)  — client deduplication key
        latitude     (str)   — GPS latitude at trigger time
        longitude    (str)   — GPS longitude at trigger time
        note         (str)   — free-text description
        triggered_at (str)   — ISO 8601 timestamp
        risk_level   (str)   — optional override
    """
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"ok": False, "error": "Invalid JSON body."}, status=400)

    try:
        sos = _create_or_get_sos(payload, request.user)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    return JsonResponse({"ok": True, "sos": _sos_to_dict(sos)}, status=201)


@csrf_exempt
@require_POST
@_api_login_required
def api_sos_sync(request):
    """
    Bulk-sync offline-queued SOS records.

    JSON body: {"records": [<sos_payload>, ...]}
    Returns a summary with per-record results.
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse({"ok": False, "error": "Invalid JSON body."}, status=400)

    records = body.get("records", [])
    if not isinstance(records, list):
        return JsonResponse({"ok": False, "error": "'records' must be a list."}, status=400)

    results = []
    synced = 0
    failed = 0

    for idx, payload in enumerate(records):
        try:
            payload["is_synced"] = True
            sos = _create_or_get_sos(payload, request.user)
            if not sos.is_synced:
                sos.is_synced = True
                sos.synced_at = timezone.now()
                sos.save(update_fields=["is_synced", "synced_at"])
            results.append({"index": idx, "ok": True, "id": sos.pk})
            synced += 1
        except Exception as exc:  # noqa: BLE001
            results.append({"index": idx, "ok": False, "error": str(exc)})
            failed += 1

    return JsonResponse({"ok": True, "synced": synced, "failed": failed, "results": results})


@require_http_methods(["GET"])
@_api_login_required
def api_sos_active(request):
    """Return all active (unresolved) SOS emergencies, newest first."""
    qs = (
        SOSEmergency.objects.filter(
            status__in=[SOSEmergency.Status.ACTIVE, SOSEmergency.Status.RESPONDING]
        )
        .select_related("mother", "triggered_by")
        .order_by("-triggered_at")
    )
    return JsonResponse({"ok": True, "emergencies": [_sos_to_dict(s) for s in qs]})


@csrf_exempt
@require_POST
@_api_login_required
def api_sos_resolve(request, pk):
    """
    Mark an SOS emergency as resolved.

    Optional JSON body: {"resolution_note": "..."}
    """
    try:
        sos = SOSEmergency.objects.get(pk=pk)
    except SOSEmergency.DoesNotExist:
        return JsonResponse({"ok": False, "error": "SOS record not found."}, status=404)

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}

    sos.status = SOSEmergency.Status.RESOLVED
    sos.resolved_by = request.user
    sos.resolved_at = timezone.now()
    sos.resolution_note = body.get("resolution_note", "")
    sos.save(update_fields=["status", "resolved_by", "resolved_at", "resolution_note"])

    logger.info("SOS pk=%s resolved by user '%s'.", sos.pk, request.user.username)
    return JsonResponse({"ok": True, "id": sos.pk, "status": "resolved"})
