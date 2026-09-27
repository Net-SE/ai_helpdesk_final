from django.conf import settings
from django.db import models

User = settings.AUTH_USER_MODEL


class KBArticle(models.Model):
    title = models.CharField(max_length=200)
    body = models.TextField()
    is_public = models.BooleanField(default=True)
    is_archived = models.BooleanField(default=False)

    created_by = models.ForeignKey(User, on_delete=models.PROTECT)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
