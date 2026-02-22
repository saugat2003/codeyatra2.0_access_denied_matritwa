from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.utils.translation import gettext_lazy as _

from .models import DoctorProfile, FCHVProfile, PatientProfile, User


@admin.register(User)
class UserAdmin(BaseUserAdmin):
    ordering = ["-date_joined"]
    list_display = ["email", "first_name", "last_name", "role", "is_onboarded", "is_active"]
    list_filter = ["role", "is_active", "is_staff", "is_onboarded"]
    search_fields = ["email", "first_name", "last_name"]

    fieldsets = (
        (None, {"fields": ("email", "password")}),
        (_('Personal info'), {"fields": ("first_name", "last_name", "phone", "role")}),
        (_('Status'), {"fields": ("is_active", "is_staff", "is_superuser", "is_onboarded")}),
        (_('Important dates'), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (None, {
            "classes": ("wide",),
            "fields": ("email", "first_name", "last_name", "role", "password1", "password2"),
        }),
    )


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "district", "province", "expected_delivery_date"]
    search_fields = ["user__email", "user__first_name", "district"]


@admin.register(DoctorProfile)
class DoctorProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "specialization", "hospital_name", "available_for_consultation"]
    search_fields = ["user__email", "specialization", "hospital_name"]


@admin.register(FCHVProfile)
class FCHVProfileAdmin(admin.ModelAdmin):
    list_display = ["user", "municipality", "district", "ward_number"]
    search_fields = ["user__email", "municipality", "district"]

