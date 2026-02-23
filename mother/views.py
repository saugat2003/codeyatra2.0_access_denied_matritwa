from django.shortcuts import render, redirect


def index(request):
    """Redirect to login or dashboard."""
    return redirect("main:dashboard")


def dashboard(request):
    """FCHV Dashboard."""
    return render(request, "mother/dashboard.html")

