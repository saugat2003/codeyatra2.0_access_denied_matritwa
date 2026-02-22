from django.test import TestCase
from django.urls import reverse


class IndexViewTests(TestCase):
    """Tests for the index view."""

    def test_index_returns_200(self):
        """GET / should return HTTP 200."""
        response = self.client.get(reverse("main:index"))
        self.assertEqual(response.status_code, 200)

    def test_index_uses_correct_template(self):
        """GET / should render main/index.html."""
        response = self.client.get(reverse("main:index"))
        self.assertTemplateUsed(response, "main/index.html")
