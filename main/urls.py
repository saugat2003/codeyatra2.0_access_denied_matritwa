from django.urls import path

from . import views

app_name = "main"

urlpatterns = [
    # Landing
    path("", views.index, name="index"),

    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),

    # Pregnancy Timeline
    path("pregnancy-timeline/", views.pregnancy_timeline, name="pregnancy_timeline"),

    # Health Streaks
    path("health-streaks/", views.health_streaks, name="health_streaks"),
    path("health-streaks/log/", views.log_health_streak, name="log_health_streak"),

    # Symptom Checker
    path("symptoms/", views.symptom_checker, name="symptom_checker"),
    path("symptoms/log/", views.log_symptom, name="log_symptom"),

    # Danger Signs
    path("danger-sign/report/", views.report_danger_sign, name="report_danger_sign"),
    path("danger-sign/<int:pk>/reported/", views.danger_sign_reported, name="danger_sign_reported"),

    # Reminders
    path("reminders/", views.reminders, name="reminders"),
    path("reminders/<int:pk>/complete/", views.complete_reminder, name="complete_reminder"),

    # Vaccinations
    path("vaccinations/", views.vaccination_details, name="vaccination_details"),
    path("vaccinations/history/", views.vaccination_history, name="vaccination_history"),
    path("vaccinations/<int:pk>/confirm/", views.confirm_vaccination, name="confirm_vaccination"),
    path("vaccinations/<int:pk>/success/", views.vaccination_confirmation, name="vaccination_confirmation"),

    # Emergency
    path("emergency-contacts/", views.emergency_contacts, name="emergency_contacts"),
    path("emergency-contacts/<int:pk>/delete/", views.delete_emergency_contact, name="delete_emergency_contact"),
    path("emergency-sos/", views.emergency_sos, name="emergency_sos"),

    # Consultation
    path("consultation/", views.doctor_consultation, name="doctor_consultation"),

    # Education
    path("education/", views.awareness_education, name="awareness_education"),
    path("education/<slug:slug>/", views.education_detail, name="education_detail"),
]
