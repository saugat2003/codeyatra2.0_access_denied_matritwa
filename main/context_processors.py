"""Custom context processors for the main app."""


def app_metadata(request):
    """Inject common app metadata into all templates."""
    return {
        "APP_NAME": "Matritwa",
        "APP_VERSION": "0.1.0",
    }
