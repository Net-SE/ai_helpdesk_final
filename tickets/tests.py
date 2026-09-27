from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.urls import reverse

from django.contrib.auth import get_user_model

from .models import SLAConfig, Ticket, TicketAttachment

User = get_user_model()


class TicketRulesTests(TestCase):
    def setUp(self):
        SLAConfig.objects.update_or_create(
            priority=Ticket.Priority.MEDIUM,
            defaults={"response_minutes": 60, "resolve_minutes": 120},
        )
        self.req = User.objects.create_user(username="req", password="pass", role=User.Role.REQUESTER)
        self.req2 = User.objects.create_user(username="req2", password="pass", role=User.Role.REQUESTER)
        self.tech = User.objects.create_user(username="tech", password="pass", role=User.Role.TECHNICIAN)
        self.tech2 = User.objects.create_user(username="tech2", password="pass", role=User.Role.TECHNICIAN)
        self.manager = User.objects.create_user(username="manager", password="pass", role=User.Role.MANAGER)

    def make_ticket(self, **kwargs):
        return Ticket.objects.create(
            requester=kwargs.pop("requester", self.req),
            title=kwargs.pop("title", "Printer issue"),
            description=kwargs.pop("description", "printer not working"),
            category=kwargs.pop("category", Ticket.Category.HARDWARE),
            priority=kwargs.pop("priority", Ticket.Priority.MEDIUM),
            assigned_to=kwargs.pop("assigned_to", None),
            **kwargs,
        )

    def test_resolution_note_required_when_resolved(self):
        ticket = self.make_ticket()
        ticket.status = Ticket.Status.RESOLVED
        ticket.resolution_note = ""
        with self.assertRaises(Exception):
            ticket.full_clean()

    def test_requester_cannot_view_other_ticket(self):
        ticket = self.make_ticket()
        self.client.login(username="req2", password="pass")
        response = self.client.get(reverse("ticket_detail", args=[ticket.pk]))
        self.assertEqual(response.status_code, 404)

    def test_technician_cannot_change_other_technicians_ticket(self):
        ticket = self.make_ticket(assigned_to=self.tech)
        self.client.login(username="tech2", password="pass")
        response = self.client.post(
            reverse("ticket_update_status", args=[ticket.pk]),
            {"status": Ticket.Status.IN_PROGRESS, "resolution_note": ""},
        )
        self.assertEqual(response.status_code, 404)

    def test_manager_can_assign(self):
        ticket = self.make_ticket()
        self.client.login(username="manager", password="pass")
        response = self.client.post(
            reverse("ticket_assign", args=[ticket.pk]),
            {"assigned_to": self.tech.pk},
        )
        self.assertEqual(response.status_code, 302)
        ticket.refresh_from_db()
        self.assertEqual(ticket.assigned_to_id, self.tech.pk)

    def test_create_ticket_with_valid_attachment(self):
        self.client.login(username="req", password="pass")
        pdf = SimpleUploadedFile("test.pdf", b"%PDF-1.4 test", content_type="application/pdf")
        response = self.client.post(
            reverse("ticket_create"),
            data={
                "title": "Printer issue",
                "description": "printer not working",
                "category": Ticket.Category.HARDWARE,
                "priority": Ticket.Priority.MEDIUM,
                "attachments": pdf,
            },
        )
        self.assertEqual(response.status_code, 302)
        ticket = Ticket.objects.latest("id")
        self.assertTrue(TicketAttachment.objects.filter(ticket=ticket).exists())

    def test_invalid_attachment_is_rejected(self):
        self.client.login(username="req", password="pass")
        bad = SimpleUploadedFile("malware.exe", b"MZ-not-an-image", content_type="application/octet-stream")
        response = self.client.post(
            reverse("ticket_create"),
            data={
                "title": "Attachment test",
                "description": "test",
                "category": Ticket.Category.OTHER,
                "priority": Ticket.Priority.LOW,
                "attachments": bad,
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(Ticket.objects.filter(title="Attachment test").exists())
