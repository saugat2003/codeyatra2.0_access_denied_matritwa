from django.contrib import messages
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, redirect

User = get_user_model()


def login_view(request):
    """Authenticate IFIC volunteer / admin and redirect to dashboard."""
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


def register_view(request):
    """Self-registration for IFIC volunteers."""
    if request.user.is_authenticated:
        return redirect("main:dashboard")

    if request.method == "POST":
        username = request.POST.get("username", "").strip()
        organization = request.POST.get("organization", "").strip()
        education = request.POST.get("education", "").strip()
        age = request.POST.get("age", "").strip()
        password1 = request.POST.get("password1", "")
        password2 = request.POST.get("password2", "")

        errors = []
        if not username:
            errors.append("Username is required.")
        elif User.objects.filter(username=username).exists():
            errors.append("That username is already taken.")
        if not password1:
            errors.append("Password is required.")
        elif password1 != password2:
            errors.append("Passwords do not match.")
        elif len(password1) < 6:
            errors.append("Password must be at least 6 characters.")
        if age and not age.isdigit():
            errors.append("Age must be a valid number.")

        if errors:
            for err in errors:
                messages.error(request, err)
        else:
            user = User.objects.create_user(
                username=username,
                password=password1,
                organization=organization,
                education=education,
                age=int(age) if age else None,
                role=User.Role.HEALTHCARE_WORKER,
            )
            login(request, user)
            messages.success(request, f"Welcome, {username}! Your account has been created.")
            return redirect("main:dashboard")

    return render(request, "accounts/register_volunteer.html")


@login_required
def logout_view(request):
    logout(request)
    messages.success(request, "You have been signed out.")
    return redirect("accounts:login")

