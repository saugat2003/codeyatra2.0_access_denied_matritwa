from django.contrib import admin

from .models import (
    ConsultationRequest,
    DangerSignReport,
    EducationContent,
    EmergencyContact,
    HealthStreak,
    PregnancyMilestone,
    Reminder,
    SymptomLog,
    Vaccination,
)


@admin.register(PregnancyMilestone)
class PregnancyMilestoneAdmin(admin.ModelAdmin):
    list_display = ["week_number", "title", "trimester", "baby_size"]
    list_filter = ["trimester"]
    ordering = ["week_number"]


@admin.register(HealthStreak)
class HealthStreakAdmin(admin.ModelAdmin):
    list_display = ["user", "date", "took_vitamins", "exercised", "drank_water", "ate_balanced_meal", "slept_well"]
    list_filter = ["date"]
    search_fields = ["user__email", "user__first_name"]


@admin.register(SymptomLog)
class SymptomLogAdmin(admin.ModelAdmin):
    list_display = ["user", "symptom", "severity", "date"]
    list_filter = ["symptom", "severity", "date"]
    search_fields = ["user__email"]


@admin.register(DangerSignReport)
class DangerSignReportAdmin(admin.ModelAdmin):
    list_display = ["user", "danger_sign", "status", "created_at"]
    list_filter = ["danger_sign", "status"]
    search_fields = ["user__email"]


@admin.register(Reminder)
class ReminderAdmin(admin.ModelAdmin):
    list_display = ["user", "title", "reminder_type", "due_date", "is_completed"]
    list_filter = ["reminder_type", "is_completed"]
    search_fields = ["user__email", "title"]


@admin.register(Vaccination)
class VaccinationAdmin(admin.ModelAdmin):
    list_display = ["user", "vaccine_name", "scheduled_date", "is_completed"]
    list_filter = ["vaccine_name", "is_completed"]
    search_fields = ["user__email"]


@admin.register(EmergencyContact)
class EmergencyContactAdmin(admin.ModelAdmin):
    list_display = ["user", "name", "relationship", "phone", "is_primary"]
    list_filter = ["relationship", "is_primary"]
    search_fields = ["user__email", "name", "phone"]


@admin.register(ConsultationRequest)
class ConsultationRequestAdmin(admin.ModelAdmin):
    list_display = ["patient", "doctor", "status", "preferred_date", "created_at"]
    list_filter = ["status"]
    search_fields = ["patient__email", "doctor__email"]


@admin.register(EducationContent)
class EducationContentAdmin(admin.ModelAdmin):
    list_display = ["title", "category", "trimester", "is_published"]
    list_filter = ["category", "trimester", "is_published"]
    search_fields = ["title"]
    prepopulated_fields = {"slug": ("title",)}
