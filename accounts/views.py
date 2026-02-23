from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect

from .models import MotherProfile, User


def login_view(request):
    """Authenticate user and redirect based on role."""
    if request.user.is_authenticated:
        return _redirect_by_role(request.user)

    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return _redirect_by_role(user)
        else:
            messages.error(request, "Invalid username or password.")
    return render(request, "accounts/login_page.html")


def logout_view(request):
    logout(request)
    return redirect("accounts:login")


# ── Multi-step mother registration ─────────────────────────────


def register_step1(request):
    """Step 1: Basic details — full_name, age, ward, phone.

    Creates the User + MotherProfile and stores the user id in session
    so subsequent steps can update the same profile.
    """
    if request.method == "POST":
        full_name = request.POST.get("full_name", "").strip()
        age = request.POST.get("age")
        ward = request.POST.get("ward", "").strip()
        phone = request.POST.get("phone", "").strip()

        if not full_name:
            messages.error(request, "Full name is required.")
            return render(request, "accounts/register_mother_step1.html")

        # Build a username from the name (lowercase, no spaces) + a short id
        import uuid

        base = full_name.lower().replace(" ", "_")[:20]
        username = f"{base}_{uuid.uuid4().hex[:6]}"

        # Create user
        user = User.objects.create_user(
            username=username,
            password="matritwa@123",  # default password; can be changed later
            role=User.Role.MOTHER,
            phone=phone,
            first_name=full_name.split()[0] if full_name else "",
            last_name=" ".join(full_name.split()[1:]) if len(full_name.split()) > 1 else "",
        )

        # Create profile
        profile = MotherProfile.objects.create(
            user=user,
            full_name=full_name,
            age=int(age) if age else None,
            ward=ward,
        )

        # Persist ids in session for next steps
        request.session["reg_user_id"] = user.pk
        request.session["reg_profile_id"] = profile.pk

        return redirect("accounts:register_step2")

    return render(request, "accounts/register_mother_step1.html")


def register_step2(request):
    """Step 2: Pregnancy details — tracking method, LMP/week, first-pregnancy,
    complications, blood group.
    """
    profile_id = request.session.get("reg_profile_id")
    if not profile_id:
        messages.warning(request, "Please start registration from Step 1.")
        return redirect("accounts:register_step1")

    if request.method == "POST":
        try:
            profile = MotherProfile.objects.get(pk=profile_id)
        except MotherProfile.DoesNotExist:
            messages.error(request, "Registration session expired. Please start over.")
            return redirect("accounts:register_step1")

        tracking = request.POST.get("tracking_method", "lmp")
        lmp_date = request.POST.get("lmp_date") or None
        pregnancy_week = request.POST.get("pregnancy_week")
        first_pregnancy = request.POST.get("first_pregnancy", "yes") == "yes"
        complications = request.POST.get("complications", "no") == "yes"
        blood_group = request.POST.get("blood_group", "")

        profile.tracking_method = tracking
        if lmp_date:
            profile.lmp_date = lmp_date
        if pregnancy_week:
            profile.pregnancy_week = int(pregnancy_week)
        profile.is_first_pregnancy = first_pregnancy
        profile.has_previous_complications = complications
        profile.blood_group = blood_group
        profile.save()

        return redirect("accounts:register_step3")

    return render(request, "accounts/register_mother_step2.html")


def register_step3(request):
    """Step 3: Location — latitude, longitude, address.

    Completes registration, logs the registering FCHV (if any), and
    optionally logs in the new mother.
    """
    profile_id = request.session.get("reg_profile_id")
    user_id = request.session.get("reg_user_id")
    if not profile_id:
        messages.warning(request, "Please start registration from Step 1.")
        return redirect("accounts:register_step1")

    if request.method == "POST":
        try:
            profile = MotherProfile.objects.get(pk=profile_id)
        except MotherProfile.DoesNotExist:
            messages.error(request, "Registration session expired. Please start over.")
            return redirect("accounts:register_step1")

        latitude = request.POST.get("latitude")
        longitude = request.POST.get("longitude")
        address = request.POST.get("address", "")

        if latitude and longitude:
            profile.latitude = latitude
            profile.longitude = longitude
        profile.address = address
        profile.registration_completed = True
        profile.save()

        # Clear session registration keys
        request.session.pop("reg_user_id", None)
        request.session.pop("reg_profile_id", None)

        messages.success(request, f"Registration complete for {profile.full_name}!")

        # If the request was made by an authenticated FCHV, redirect to dashboard
        if request.user.is_authenticated and request.user.is_healthcare_worker:
            return redirect("main:dashboard")

        # Otherwise log in the new mother
        new_user = profile.user
        login(request, new_user)
        return redirect("main:dashboard")

    return render(request, "accounts/register_mother_step3.html")


# ── Helpers ─────────────────────────────────────────────────────


def _redirect_by_role(user):
    """Send the user to the appropriate dashboard after login."""
    if user.role == User.Role.HEALTHCARE_WORKER:
        return redirect("main:dashboard")
    elif user.role == User.Role.MOTHER:
        return redirect("main:mother_profile", pk=user.pk)
    return redirect("main:dashboard")
