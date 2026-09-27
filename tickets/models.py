from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.utils import timezone
from datetime import timedelta

User = settings.AUTH_USER_MODEL


class SLAConfig(models.Model):
    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    priority = models.CharField(max_length=10, choices=Priority.choices, unique=True)
    response_minutes = models.PositiveIntegerField(default=240)
    resolve_minutes = models.PositiveIntegerField(default=1440)

    def __str__(self):
        return f"{self.priority}: resp {self.response_minutes}m / res {self.resolve_minutes}m"


class Ticket(models.Model):
    class Category(models.TextChoices):
        HARDWARE = "HARDWARE", "Hardware"
        SOFTWARE = "SOFTWARE", "Software"
        NETWORK = "NETWORK", "Network"
        ACCOUNT = "ACCOUNT", "Account Access"
        OTHER = "OTHER", "Other"

    class Priority(models.TextChoices):
        LOW = "LOW", "Low"
        MEDIUM = "MEDIUM", "Medium"
        HIGH = "HIGH", "High"
        CRITICAL = "CRITICAL", "Critical"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        IN_PROGRESS = "IN_PROGRESS", "In Progress"
        RESOLVED = "RESOLVED", "Resolved"
        CLOSED = "CLOSED", "Closed"

    requester = models.ForeignKey(
        User, on_delete=models.PROTECT, related_name="requested_tickets"
    )
    assigned_to = models.ForeignKey(
        User,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        related_name="assigned_tickets",
    )

    title = models.CharField(max_length=200)
    description = models.TextField()

    category = models.CharField(
        max_length=20, choices=Category.choices, default=Category.OTHER
    )
    priority = models.CharField(
        max_length=10, choices=Priority.choices, default=Priority.MEDIUM
    )
    status = models.CharField(
        max_length=20, choices=Status.choices, default=Status.OPEN
    )

    resolution_note = models.TextField(blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    first_response_at = models.DateTimeField(null=True, blank=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
    closed_at = models.DateTimeField(null=True, blank=True)

    due_response_at = models.DateTimeField(null=True, blank=True)
    due_resolve_at = models.DateTimeField(null=True, blank=True)

    is_archived = models.BooleanField(default=False)

    def display_id(self) -> str:
        return f"HD-{self.pk:06d}" if self.pk else "HD-NEW"

    def clean(self):
        # enforce status transitions
        if not self.pk:
            return
        old = Ticket.objects.get(pk=self.pk)
        allowed = {
            self.Status.OPEN: {
                self.Status.IN_PROGRESS,
                self.Status.RESOLVED,
                self.Status.CLOSED,
                self.Status.OPEN,
            },
            self.Status.IN_PROGRESS: {
                self.Status.RESOLVED,
                self.Status.CLOSED,
                self.Status.IN_PROGRESS,
            },
            self.Status.RESOLVED: {self.Status.CLOSED, self.Status.RESOLVED},
            self.Status.CLOSED: {self.Status.CLOSED},
        }
        if self.status not in allowed.get(old.status, {old.status}):
            raise ValidationError(
                f"Invalid status transition: {old.status} -> {self.status}"
            )
        if self.status == self.Status.RESOLVED and not self.resolution_note.strip():
            raise ValidationError(
                "Resolution Note is required when status is Resolved."
            )

    ai_category = models.CharField(max_length=20, blank=True, default="")
    ai_priority = models.CharField(max_length=10, blank=True, default="")
    ai_confidence = models.FloatField(default=0.0)

    response_risk_alerted_at = models.DateTimeField(null=True, blank=True)
    resolve_risk_alerted_at = models.DateTimeField(null=True, blank=True)
    breach_alerted_at = models.DateTimeField(null=True, blank=True)

    @property
    def met_response_sla(self) -> bool:
        return bool(
            self.first_response_at
            and self.due_response_at
            and self.first_response_at <= self.due_response_at
        )

    @property
    def met_resolve_sla(self) -> bool:
        return bool(
            self.resolved_at
            and self.due_resolve_at
            and self.resolved_at <= self.due_resolve_at
        )

    @property
    def first_response_minutes(self):
        if not self.first_response_at:
            return None
        delta = self.first_response_at - self.created_at
        return int(delta.total_seconds() // 60)

    @property
    def resolution_minutes(self):
        if not self.resolved_at:
            return None
        delta = self.resolved_at - self.created_at
        return int(delta.total_seconds() // 60)

    def apply_sla(self):
        sla = SLAConfig.objects.filter(priority=self.priority).first()
        if not sla:
            return
        base = self.created_at or timezone.now()
        self.due_response_at = base + timedelta(minutes=sla.response_minutes)
        self.due_resolve_at = base + timedelta(minutes=sla.resolve_minutes)

    def save(self, *args, **kwargs):
        creating = self.pk is None
        super().save(*args, **kwargs)
        if creating:
            self.apply_sla()
            super().save(update_fields=["due_response_at", "due_resolve_at"])

    @property
    def is_sla_response_breached(self) -> bool:
        return bool(
            self.due_response_at
            and not self.first_response_at
            and timezone.now() > self.due_response_at
        )

    @property
    def is_sla_resolve_breached(self) -> bool:
        return bool(
            self.due_resolve_at
            and not self.resolved_at
            and timezone.now() > self.due_resolve_at
        )


def ticket_attachment_path(instance, filename):
    # tickets/<ticket_id>/<filename>
    return f"tickets/{instance.ticket_id}/{filename}"


def validate_attachment(file):
    """Validate extension, size and basic file signature/content."""
    import os
    from io import BytesIO

    ext = os.path.splitext(file.name)[1].lower()
    allowed = {".png", ".jpg", ".jpeg", ".pdf"}
    if ext not in allowed:
        raise ValidationError("Only PNG, JPG, JPEG and PDF files are allowed.")
    if file.size > 10 * 1024 * 1024:
        raise ValidationError("File size must be <= 10MB.")

    head = file.read(16)
    file.seek(0)
    signatures = {
        ".pdf": head.startswith(b"%PDF-"),
        ".png": head.startswith(b"\x89PNG\r\n\x1a\n"),
        ".jpg": head.startswith(b"\xff\xd8\xff"),
        ".jpeg": head.startswith(b"\xff\xd8\xff"),
    }
    if not signatures.get(ext, False):
        raise ValidationError("The uploaded file content does not match its extension.")

    if ext in {".png", ".jpg", ".jpeg"}:
        try:
            from PIL import Image
            image = Image.open(BytesIO(file.read()))
            image.verify()
        except Exception as exc:
            raise ValidationError("The image file is invalid or corrupted.") from exc
        finally:
            file.seek(0)


class TicketAttachment(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="attachments"
    )
    file = models.FileField(
        upload_to=ticket_attachment_path, validators=[validate_attachment]
    )
    uploaded_by = models.ForeignKey(User, on_delete=models.PROTECT)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    @property
    def ticket_id(self):
        return self.ticket.pk


class TicketComment(models.Model):
    ticket = models.ForeignKey(
        Ticket, on_delete=models.CASCADE, related_name="comments"
    )
    author = models.ForeignKey(User, on_delete=models.PROTECT)
    message = models.TextField()
    is_internal = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
