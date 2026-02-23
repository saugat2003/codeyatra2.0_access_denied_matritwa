"""
SOS Emergency REST-style API (offline-first).

Endpoints
─────────
POST   /api/sos/          Create a single SOS emergency
POST   /api/sos/sync/     Bulk-sync queued offline SOS records
GET    /api/sos/pending/   List active (unresolved) emergencies
POST   /api/sos/<id>/resolve/   Mark an SOS as resolved

All responses are JSON.  Authentication: session-based (Django's
``@login_required`` through a helper decorator that returns 401
instead of redirecting).
"""

import json
import uuid as _uuid
from datetime import datetime

from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST, require_http_methods

from accounts.models import MotherProfile
from .models import Alert, SOSEmergency


# ── Auth helper ─────────────────────────────────────────────────


def _api_login_required(view_fn):
    """Return 401 JSON instead of redirecting to the login page."""
    from functools import wraps

    @wraps(view_fn)
    def wrapper(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return JsonResponse(
                {"ok": False, "error": "Authentication required."},
                status=401,
            )
        return view_fn(request, *args, **kwargs)

    return wrapper


# ── Helpers ─────────────────────────────────────────────────────


def _compute_risk_level(mother: MotherProfile) -> str:
    """
    Derive a risk level from the mother's clinical data.

    Uses ANC danger-sign history, pregnancy week, age and
    complication flag to decide urgency.
    """
    from .models import ANCVisit

    danger_visits = ANCVisit.objects.filter(
        mother=mother, has_danger_signs=True,
    ).count()

    week = mother.pregnancy_week or 0
    age = mother.age or 25

    # Critical: danger signs seen ≥2 times, or week ≥37 with complications
    if danger_visits >= 2:
        return SOSEmergency.RiskLevel.CRITICAL
    if week >= 37 and mother.has_previous_complications:
        return SOSEmergency.RiskLevel.CRITICAL

    # High: any danger sign, or age <18 / >35 with complications
    if danger_visits >= 1:
        return SOSEmergency.RiskLevel.HIGH
    if (age < 18 or age > 35) and mother.has_previous_complications:
        return SOSEmergency.RiskLevel.HIGH

    # Moderate: previous complications
    if mother.has_previous_complications:
        return SOSEmergency.RiskLevel.MODERATE

    return SOSEmergency.RiskLevel.LOW


def _sos_to_dict(sos: SOSEmergency) -> dict:
    """Serialize an SOSEmergency record to a JSON-friendly dict."""
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
        "triggered_by": (
            sos.triggered_by.get_full_name() if sos.triggered_by else ""
        ),
        "is_synced": sos.is_synced,
        "time_ago": sos.time_ago,
    }


def _create_sos_from_payload(payload: dict, user) -> SOSEmergency:
    """
    Create (or deduplicate) an SOSEmergency from a dict payload.

    Returns the created / existing SOSEmergency instance.
    Raises ValueError with a human message on bad input.
    """
    mother_id = payload.get("mother_id")
    if not mother_id:
        raise ValueError("mother_id is required.")

    try:
        mother = MotherProfile.objects.get(pk=mother_id)
    except MotherProfile.DoesNotExist:
        raise ValueError(f"Mother with id={mother_id} not found.")

    # Parse offline_id (client should always send one)
    raw_oid = payload.get("offline_id")
    try:
        offline_id = _uuid.UUID(str(raw_oid)) if raw_oid else _uuid.uuid4()
    except (ValueError, AttributeError):
        offline_id = _uuid.uuid4()

    # Deduplicate: if offline_id already saved, return existing
    existing = SOSEmergency.objects.filter(offline_id=offline_id).first()
    if existing:
        return existing

    # Parse triggered_at (ISO 8601 from client, fallback to now)
    raw_ts = payload.get("triggered_at")
    try:
        triggered_at = datetime.fromisoformat(raw_ts) if raw_ts else timezone.now()
    except (ValueError, TypeError):
        triggered_at = timezone.now()
    if timezone.is_naive(triggered_at):
        triggered_at = timezone.make_aware(triggered_at)

    risk_level = payload.get("risk_level") or _compute_risk_level(mother)

    sos = SOSEmergency.objects.create(
        offline_id=offline_id,
        mother=mother,
        triggered_by=user if user.is_authenticated else None,
        risk_level=risk_level,
        latitude=payload.get("latitude") or mother.latitude,
        longitude=payload.get("longitude") or mother.longitude,
        note=payload.get("note", ""),
        triggered_at=triggered_at,
        is_synced=payload.get("is_synced", True),
        synced_at=timezone.now() if payload.get("is_synced", True) else None,
    )

    # Also create a legacy Alert so the priority_alerts page picks it up
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

    return sos


# ── Endpoints ───────────────────────────────────────────────────


@csrf_exempt
@require_POST
@_api_login_required
def api_sos_create(request):
    """
    Create a single SOS emergency.

    Accepts ``application/json`` with keys:
        mother_id      (int)  — required
        offline_id     (uuid) — client-generated dedup key
        latitude       (str)  — GPS lat at trigger time
        longitude      (str)  — GPS lng at trigger time
        note           (str)  — free-text description
        triggered_at   (str)  — ISO 8601 timestamp
        risk_level     (str)  — optional override
    """
    try:
        payload = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse(
            {"ok": False, "error": "Invalid JSON body."}, status=400,
        )

    try:
        sos = _create_sos_from_payload(payload, request.user)
    except ValueError as exc:
        return JsonResponse({"ok": False, "error": str(exc)}, status=400)

    return JsonResponse({"ok": True, "sos": _sos_to_dict(sos)}, status=201)


@csrf_exempt
@require_POST
@_api_login_required
def api_sos_sync(request):
    """
    Bulk-sync offline-queued SOS records.

    Accepts ``application/json`` with key ``records`` (list of SOS
    payloads identical to ``api_sos_create``).

    Returns a summary with counts and per-record results.
    """
    try:
        body = json.loads(request.body)
    except (json.JSONDecodeError, TypeError):
        return JsonResponse(
            {"ok": False, "error": "Invalid JSON body."}, status=400,
        )

    records = body.get("records", [])
    if not isinstance(records, list):
        return JsonResponse(
            {"ok": False, "error": "'records' must be a list."}, status=400,
        )

    results = []
    synced = 0
    failed = 0

    for idx, payload in enumerate(records):
        try:
            payload["is_synced"] = True
            sos = _create_sos_from_payload(payload, request.user)
            # Mark as synced now
            if not sos.is_synced:
                sos.is_synced = True
                sos.synced_at = timezone.now()
                sos.save(update_fields=["is_synced", "synced_at"])
            results.append({"index": idx, "ok": True, "id": sos.pk})
            synced += 1
        except (ValueError, Exception) as exc:
            results.append({"index": idx, "ok": False, "error": str(exc)})
            failed += 1

    return JsonResponse({
        "ok": True,
        "synced": synced,
        "failed": failed,
        "results": results,
    })


@require_http_methods(["GET"])
@_api_login_required
def api_sos_active(request):
    """
    Return all active (unresolved) SOS emergencies.

    Ordered newest-first.  Useful for the FCHV dashboard.
    """
    qs = (
        SOSEmergency.objects
        .filter(status__in=[SOSEmergency.Status.ACTIVE, SOSEmergency.Status.RESPONDING])
        .select_related("mother", "triggered_by")
        .order_by("-triggered_at")
    )
    return JsonResponse({
        "ok": True,
        "emergencies": [_sos_to_dict(s) for s in qs],
    })


@csrf_exempt
@require_POST
@_api_login_required
def api_sos_resolve(request, pk):
    """
    Mark an SOS emergency as resolved.

    Accepts optional JSON body with ``resolution_note``.
    """
    try:
        sos = SOSEmergency.objects.get(pk=pk)
    except SOSEmergency.DoesNotExist:
        return JsonResponse(
            {"ok": False, "error": "SOS record not found."}, status=404,
        )

    try:
        body = json.loads(request.body) if request.body else {}
    except json.JSONDecodeError:
        body = {}

    sos.status = SOSEmergency.Status.RESOLVED
    sos.resolved_by = request.user
    sos.resolved_at = timezone.now()
    sos.resolution_note = body.get("resolution_note", "")
    sos.save(update_fields=[
        "status", "resolved_by", "resolved_at", "resolution_note",
    ])

    return JsonResponse({"ok": True, "id": sos.pk, "status": "resolved"})
