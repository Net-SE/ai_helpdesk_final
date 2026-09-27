from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


class OpsPermissionTests(TestCase):
    def test_requester_cannot_access_ops_dashboard(self):
        user = User.objects.create_user(username="req", password="pass", role=User.Role.REQUESTER)
        self.client.login(username="req", password="pass")
        response = self.client.get(reverse("ops_dashboard"))
        self.assertEqual(response.status_code, 403)

    def test_manager_can_access_ops_dashboard(self):
        User.objects.create_user(username="manager", password="pass", role=User.Role.MANAGER)
        self.client.login(username="manager", password="pass")
        response = self.client.get(reverse("ops_dashboard"))
        self.assertEqual(response.status_code, 200)
