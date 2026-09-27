from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

User = get_user_model()


class AIFallbackTests(TestCase):
    def setUp(self):
        self.u = User.objects.create_user(username="u", password="pass", role=User.Role.REQUESTER)

    def test_ai_fallback_when_exception(self):
        self.client.login(username="u", password="pass")
        with patch("aiassist.views.classify_text", side_effect=Exception("AI down")):
            response = self.client.get(reverse("ai_suggest") + "?text=hello")
            self.assertEqual(response.status_code, 200)
            self.assertTrue(response.json()["fallback"])

    def test_ai_endpoint_requires_login(self):
        response = self.client.get(reverse("ai_suggest") + "?text=hello")
        self.assertIn(response.status_code, (302, 403))
