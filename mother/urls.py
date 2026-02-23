from django.urls import path

from . import api, views

app_name = "main"

urlpatterns = [
    # Index / Landing
    path("", views.index, name="index"),

    # Dashboard
    path("dashboard/", views.dashboard, name="dashboard"),

    # Register Mother (FCHV only)
    path("register/", views.register_mother, name="register_mother"),

    # Mother Records
    path("mothers/", views.mother_list, name="mother_list"),
    path("mothers/<int:pk>/", views.mother_profile, name="mother_profile"),
    path("mothers/<int:pk>/anc/", views.update_anc_visit, name="update_anc_visit"),
    path("mothers/<int:pk>/consult/", views.hospital_consultation, name="hospital_consultation"),
    path("mothers/<int:pk>/photo/", views.update_photo, name="update_photo"),
    path("mothers/<int:pk>/sos/", views.trigger_sos, name="trigger_sos"),
    path("mothers/<int:pk>/sos/trigger/", views.sos_trigger_page, name="sos_trigger_page"),
    path("mothers/<int:pk>/sos/history/", views.sos_history, name="sos_history"),

    # Alert management
    path("alerts/<int:pk>/resolve/", views.resolve_alert, name="resolve_alert"),

    # Records & Reports
    path("records/", views.records_detail, name="records_detail"),
    path("reports/", views.monthly_reports, name="monthly_reports"),

    # Alerts
    path("alerts/", views.priority_alerts, name="priority_alerts"),

    # Awareness Programs
    path("awareness/create/", views.awareness_program, name="awareness_program"),

    # ── SOS Emergency API (offline-first) ───────────────────────
    path("api/sos/", api.api_sos_create, name="api_sos_create"),
    path("api/sos/sync/", api.api_sos_sync, name="api_sos_sync"),
    path("api/sos/active/", api.api_sos_active, name="api_sos_active"),
    path("api/sos/<int:pk>/resolve/", api.api_sos_resolve, name="api_sos_resolve"),
]
