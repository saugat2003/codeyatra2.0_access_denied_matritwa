from django.urls import path

from . import views

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
    
    # Records & Reports
    path("records/", views.records_detail, name="records_detail"),
    path("reports/", views.monthly_reports, name="monthly_reports"),
    
    # Alerts
    path("alerts/", views.priority_alerts, name="priority_alerts"),
    
    # Awareness Programs
    path("awareness/create/", views.awareness_program, name="awareness_program"),
]
