from django.shortcuts import render


def index(request):
    """Render the landing page."""
    return render(request, "main/index.html")


def welcome_to_matritwa(request):
    return render(request, "main/welcome_to_matritwa.html")


def user_registration(request):
    return render(request, "main/user_registration.html")


def personalize_your_journey(request):
    return render(request, "main/personalize_your_journey.html")


def welcome_dashboard(request):
    return render(request, "main/welcome_dashboard.html")


def pregnancy_timeline(request):
    return render(request, "main/pregnancy_timeline.html")


def health_streaks_tracker(request):
    return render(request, "main/health_streaks_tracker.html")


def awareness_education(request):
    return render(request, "main/awareness_education.html")


def smart_symptom_checker(request):
    return render(request, "main/smart_symptom_checker.html")


def report_danger_sign(request):
    return render(request, "main/report_danger_sign.html")


def danger_sign_reported(request):
    return render(request, "main/danger_sign_reported.html")


def emergency_contacts(request):
    return render(request, "main/emergency_contacts.html")


def emergency_sos_details(request):
    return render(request, "main/emergency_sos_details.html")


def reminders_notifications(request):
    return render(request, "main/reminders_notifications.html")


def doctor_consultation(request):
    return render(request, "main/doctor_consultation.html")


def vaccination_history(request):
    return render(request, "main/vaccination_history.html")


def vaccination_details(request):
    return render(request, "main/vaccination_details.html")


def vaccination_confirmation_success(request):
    return render(request, "main/vaccination_confirmation_success.html")


def patient_monitoring_profile(request):
    return render(request, "main/patient_monitoring_profile.html")


def fchv_dashboard(request):
    return render(request, "main/fchv_dashboard.html")


def doctors_dashboard(request):
    return render(request, "main/doctors_dashboard.html")
