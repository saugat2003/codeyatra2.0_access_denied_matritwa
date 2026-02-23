from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect


def login_view(request):
    """Authenticate FCHV / admin and redirect to dashboard."""
    if request.user.is_authenticated:
        return redirect("main:dashboard")

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("main:dashboard")
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, "accounts/login_page.html")


@login_required
def logout_view(request):
    logout(request)
    return redirect("accounts:login")

