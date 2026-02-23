from django.contrib import admin

from .models import ANCVisit, AwarenessProgram, HospitalConsultation


@admin.register(ANCVisit)
class ANCVisitAdmin(admin.ModelAdmin):
    list_display = ("mother", "visit_number", "visit_date", "has_danger_signs", "recorded_by")
    list_filter = ("has_danger_signs", "visit_date")
    search_fields = ("mother__full_name",)


@admin.register(AwarenessProgram)
class AwarenessProgramAdmin(admin.ModelAdmin):
    list_display = ("topic", "event_datetime", "location", "created_by")
    list_filter = ("topic",)
    filter_horizontal = ("attendees",)


@admin.register(HospitalConsultation)
class HospitalConsultationAdmin(admin.ModelAdmin):
    list_display = ("mother", "reference_id", "is_synced", "referred_by", "created_at")
    list_filter = ("is_synced",)
    search_fields = ("mother__full_name", "reference_id")
