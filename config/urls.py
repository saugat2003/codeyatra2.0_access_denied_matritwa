"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
"""

from django.conf import settings
from django.conf.urls.static import static
from django.contrib import admin
from django.urls import include, path
from django.views.static import serve as static_serve

urlpatterns = [
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls", namespace="accounts")),
    path("healthcare/", include("healthcare.urls", namespace="healthcare")),

    # Service Worker must be served from root for maximum scope
    path(
        "sw.js",
        static_serve,
        {"document_root": settings.STATICFILES_DIRS[0], "path": "sw.js"},
        name="service_worker",
    ),
    path(
        "manifest.json",
        static_serve,
        {"document_root": settings.STATICFILES_DIRS[0], "path": "manifest.json"},
        name="manifest",
    ),

    path("", include("mother.urls", namespace="main")),
]

# Serve media files during development
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
