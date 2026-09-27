from django.test import TestCase
from django.urls import reverse


class HealthTests(TestCase):
    def test_health_endpoint(self):
        response = self.client.get(reverse("healthz"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_request_id_header_exists(self):
        response = self.client.get(reverse("healthz"))
        self.assertIn("X-Request-ID", response)
