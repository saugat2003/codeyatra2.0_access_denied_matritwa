from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, redirect


def login_view(request):
    if request.method == "POST":
        username = request.POST.get("username")
        password = request.POST.get("password")
        user = authenticate(request, username=username, password=password)
        if user is not None:
            login(request, user)
            return redirect("healthcare:dashboard")
        else:
            from django.contrib import messages
            messages.error(request, "Invalid username or password.")
    return render(request, "accounts/login_page.html")


def logout_view(request):
    logout(request)
    return redirect("accounts:login")


def register_step1(request):
    return render(request, "accounts/register_mother_step1.html")


def register_step2(request):
    return render(request, "accounts/register_mother_step2.html")


def register_step3(request):
    return render(request, "accounts/register_mother_step3.html")
