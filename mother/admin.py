from django.contrib import admin

from .models import (
    ANCVisit, Alert, AwarenessProgram, HospitalConsultation,
    MonthlyReport, ScheduledVisit, SOSEmergency,
)


@admin.register(ANCVisit)
class ANCVisitAdmin(admin.ModelAdmin):
    list_display = ("mother", "visit_number", "visit_date", "weight_kg", "blood_pressure", "has_danger_signs", "recorded_by")
    list_filter = ("has_danger_signs", "visit_date")
    search_fields = ("mother__full_name",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(AwarenessProgram)
class AwarenessProgramAdmin(admin.ModelAdmin):
    list_display = ("topic", "event_datetime", "location", "created_by", "created_at")
    list_filter = ("topic",)
    filter_horizontal = ("attendees",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(HospitalConsultation)
class HospitalConsultationAdmin(admin.ModelAdmin):
    list_display = ("mother", "reference_id", "is_synced", "referred_by", "created_at")
    list_filter = ("is_synced",)
    search_fields = ("mother__full_name", "reference_id")
    readonly_fields = ("created_at", "updated_at")


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = ("title", "mother", "alert_type", "priority", "is_read", "is_resolved", "assigned_to", "created_at")
    list_filter = ("alert_type", "priority", "is_read", "is_resolved")
    search_fields = ("title", "mother__full_name", "message")
    list_editable = ("is_read", "is_resolved")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("mother", "assigned_to")


@admin.register(ScheduledVisit)
class ScheduledVisitAdmin(admin.ModelAdmin):
    list_display = ("mother", "visit_type", "visit_number", "scheduled_date", "scheduled_time", "is_completed", "is_overdue")
    list_filter = ("visit_type", "is_completed", "scheduled_date")
    search_fields = ("mother__full_name",)
    list_editable = ("is_completed",)
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("mother", "completed_visit")

    @admin.display(boolean=True, description="Overdue?")
    def is_overdue(self, obj):
        return obj.is_overdue


@admin.register(MonthlyReport)
class MonthlyReportAdmin(admin.ModelAdmin):
    list_display = (
        "year", "month", "new_registrations", "total_anc_visits",
        "high_risk_cases", "stable_cases", "goal_progress", "generated_by",
    )
    list_filter = ("year", "month")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("generated_by",)

    @admin.display(description="Goal %")
    def goal_progress(self, obj):
        return f"{obj.goal_progress}%"


@admin.register(SOSEmergency)
class SOSEmergencyAdmin(admin.ModelAdmin):
    """Admin view for SOS Emergency records."""

    list_display = (
        "offline_id_short", "mother", "risk_level", "status",
        "is_synced", "triggered_at", "triggered_by",
    )
    list_filter = ("status", "risk_level", "is_synced")
    search_fields = ("mother__full_name", "note", "offline_id")
    readonly_fields = (
        "offline_id", "triggered_at", "synced_at", "resolved_at",
        "created_at", "updated_at",
    )
    raw_id_fields = ("mother", "triggered_by", "resolved_by")
    list_editable = ("status",)
    date_hierarchy = "triggered_at"

    @admin.display(description="Offline ID")
    def offline_id_short(self, obj):
        """Show truncated offline_id for readability."""
        return str(obj.offline_id)[:8]
