from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin

from .models import MotherProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    fieldsets = BaseUserAdmin.fieldsets + (
        (
            "FCHV / Volunteer Info",
            {"fields": ("phone", "organization", "education", "age", "role")},
        ),
    )
    add_fieldsets = BaseUserAdmin.add_fieldsets + (
        (
            "FCHV / Volunteer Info",
            {"fields": ("phone", "organization", "education", "age", "role")},
        ),
    )
    list_display = ("username", "get_full_name", "email", "role", "organization", "is_staff", "is_active")
    list_filter = ("role", "is_staff", "is_active")
    search_fields = ("username", "first_name", "last_name", "email", "organization")


@admin.register(MotherProfile)
class MotherProfileAdmin(admin.ModelAdmin):
    list_display = (
        "full_name", "age", "phone", "emergency_contact",
        "pregnancy_week", "blood_group", "ward", "registered_by",
        "registration_completed", "created_at",
    )
    list_filter = ("registration_completed", "is_first_pregnancy", "has_previous_complications", "blood_group")
    search_fields = ("full_name", "phone", "emergency_contact", "ward")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("registered_by",)
    fieldsets = (
        ("Identity", {"fields": ("full_name", "age", "phone", "emergency_contact", "photo")}),
        ("Pregnancy", {
            "fields": (
                "pregnancy_week", "lmp_date", "is_first_pregnancy",
                "has_previous_complications", "blood_group", "medical_notes",
            )
        }),
        ("Location", {"fields": ("ward", "address", "latitude", "longitude")}),
        ("Meta", {"fields": ("registered_by", "registration_completed", "created_at", "updated_at")}),
    )
