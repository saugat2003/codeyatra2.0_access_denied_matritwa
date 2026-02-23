from django.urls import path

from . import views

app_name = "main"

urlpatterns = [
    path("", views.index, name="index"),
    path("dashboard/", views.dashboard, name="dashboard"),
    path("mothers/", views.mother_list, name="mother_list"),
    path("mothers/<int:pk>/", views.mother_profile, name="mother_profile"),
    path("mothers/<int:pk>/anc/", views.update_anc_visit, name="update_anc_visit"),
    path("mothers/<int:pk>/consult/", views.hospital_consultation, name="hospital_consultation"),
    path("awareness/create/", views.awareness_program, name="awareness_program"),
]
