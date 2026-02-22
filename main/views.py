from django.shortcuts import render


def index(request):
    """Render the landing page."""
    return render(request, "main/index.html")
