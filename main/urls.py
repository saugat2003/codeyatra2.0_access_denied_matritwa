from django.urls import path

from . import views

app_name = "main"

urlpatterns = [
    # Landing
    path("", views.index, name="index"),
    path("welcome/", views.welcome_to_matritwa, name="welcome"),

    # Onboarding
    path("register/", views.user_registration, name="user_registration"),
    path("personalize/", views.personalize_your_journey, name="personalize_your_journey"),

    # Dashboard
    path("dashboard/", views.welcome_dashboard, name="welcome_dashboard"),
    path("dashboard/fchv/", views.fchv_dashboard, name="fchv_dashboard"),
    path("dashboard/doctor/", views.doctors_dashboard, name="doctors_dashboard"),

    # Pregnancy & Health
    path("pregnancy/timeline/", views.pregnancy_timeline, name="pregnancy_timeline"),
    path("health/streaks/", views.health_streaks_tracker, name="health_streaks_tracker"),
    path("health/awareness/", views.awareness_education, name="awareness_education"),

    # Symptoms & Danger Signs
    path("symptoms/checker/", views.smart_symptom_checker, name="smart_symptom_checker"),
    path("danger/report/", views.report_danger_sign, name="report_danger_sign"),
    path("danger/reported/", views.danger_sign_reported, name="danger_sign_reported"),

    # Emergency
    path("emergency/contacts/", views.emergency_contacts, name="emergency_contacts"),
    path("emergency/sos/", views.emergency_sos_details, name="emergency_sos_details"),

    # Reminders & Consultations
    path("reminders/", views.reminders_notifications, name="reminders_notifications"),
    path("consultation/doctor/", views.doctor_consultation, name="doctor_consultation"),

    # Vaccinations
    path("vaccination/history/", views.vaccination_history, name="vaccination_history"),
    path("vaccination/details/", views.vaccination_details, name="vaccination_details"),
    path("vaccination/success/", views.vaccination_confirmation_success, name="vaccination_confirmation_success"),

    # Patient Monitoring
    path("patient/profile/", views.patient_monitoring_profile, name="patient_monitoring_profile"),
]
