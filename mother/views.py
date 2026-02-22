from django.shortcuts import render, redirect


def index(request):
    """Redirect to login for unauthenticated users."""
    return redirect("accounts:login")

