from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse

from .models import KBArticle

User = get_user_model()


class KnowledgeBasePermissionTests(TestCase):
    def setUp(self):
        self.req = User.objects.create_user(username="req", password="pass", role=User.Role.REQUESTER)
        self.tech = User.objects.create_user(username="tech", password="pass", role=User.Role.TECHNICIAN)
        self.article = KBArticle.objects.create(
            title="Private guide", body="secret internal solution", is_public=False, created_by=self.tech
        )

    def test_requester_cannot_read_private_article(self):
        self.client.login(username="req", password="pass")
        response = self.client.get(reverse("kb_detail", args=[self.article.pk]))
        self.assertEqual(response.status_code, 404)

    def test_technician_can_edit_article(self):
        self.client.login(username="tech", password="pass")
        response = self.client.post(
            reverse("kb_edit", args=[self.article.pk]),
            {"title": "Updated guide", "body": "updated", "is_public": "on"},
        )
        self.assertEqual(response.status_code, 302)
        self.article.refresh_from_db()
        self.assertEqual(self.article.title, "Updated guide")

    def test_technician_can_archive_article(self):
        self.client.login(username="tech", password="pass")
        response = self.client.post(reverse("kb_archive", args=[self.article.pk]))
        self.assertEqual(response.status_code, 302)
        self.article.refresh_from_db()
        self.assertTrue(self.article.is_archived)
