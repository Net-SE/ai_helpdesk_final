import base64
import json
from django.test import TestCase
from django.urls import reverse
from accounts.models import User
from tickets.models import Ticket


class APITests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(username="api_req", password="Password123!", role=User.Role.REQUESTER)
        cls.tech = User.objects.create_user(username="api_tech", password="Password123!", role=User.Role.TECHNICIAN)
        cls.manager = User.objects.create_user(username="api_manager", password="Password123!", role=User.Role.MANAGER)

    def auth(self, username, password="Password123!"):
        token = base64.b64encode(f"{username}:{password}".encode()).decode()
        self.client.defaults["HTTP_AUTHORIZATION"] = f"Basic {token}"

    def test_health(self):
        response = self.client.get(reverse("api_health"))
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["ok"])

    def test_tickets_require_auth(self):
        response = self.client.get(reverse("api_tickets"))
        self.assertEqual(response.status_code, 401)

    def test_requester_can_create_ticket(self):
        self.auth("api_req")
        response = self.client.post(reverse("api_tickets"), data=json.dumps({"title":"Printer problem","description":"Printer is not working"}), content_type="application/json")
        self.assertEqual(response.status_code, 201)
        self.assertEqual(Ticket.objects.count(), 1)
        self.assertEqual(response.json()["ticket"]["category"], Ticket.Category.HARDWARE)

    def test_requester_cannot_assign(self):
        ticket = Ticket.objects.create(requester=self.user, title="Test", description="Test")
        self.auth("api_req")
        response = self.client.post(reverse("api_ticket_assign", args=[ticket.pk]), data=json.dumps({"technician_id": self.tech.pk}), content_type="application/json")
        self.assertEqual(response.status_code, 403)

    def test_manager_can_assign(self):
        ticket = Ticket.objects.create(requester=self.user, title="Test", description="Test")
        self.auth("api_manager")
        response = self.client.post(reverse("api_ticket_assign", args=[ticket.pk]), data=json.dumps({"technician_id": self.tech.pk}), content_type="application/json")
        self.assertEqual(response.status_code, 200)
        ticket.refresh_from_db()
        self.assertEqual(ticket.assigned_to_id, self.tech.pk)
