from django import forms
from .models import Ticket, TicketComment
from .models import SLAConfig
from accounts.models import User


class TicketCreateForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["title", "description", "category", "priority"]
        widgets = {
            "title": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Short summary (e.g., Printer not working)",
                }
            ),
            "description": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 5,
                    "placeholder": "Describe the problem details...",
                }
            ),
            "category": forms.Select(attrs={"class": "form-select"}),
            "priority": forms.Select(attrs={"class": "form-select"}),
        }


class TicketStatusForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["status", "resolution_note"]
        widgets = {
            "status": forms.Select(attrs={"class": "form-select"}),
            "resolution_note": forms.Textarea(
                attrs={"class": "form-control", "rows": 4}
            ),
        }


class TicketAssignForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ["assigned_to"]
        widgets = {
            "assigned_to": forms.Select(attrs={"class": "form-select ticket-assigned-select"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["assigned_to"].queryset = User.objects.filter(
            role__in=[User.Role.TECHNICIAN, User.Role.MANAGER, User.Role.ADMIN],
            is_active=True,
        ).order_by("username")


class CommentForm(forms.ModelForm):

    class Meta:
        model = TicketComment

        fields = [
            "message",
            "is_internal",
        ]

        widgets = {
            "message": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Write your message...",
                }
            ),
            "is_internal": forms.CheckboxInput(
                attrs={
                    "class": "form-check-input",
                }
            ),
        }


class SLAConfigForm(forms.ModelForm):
    class Meta:
        model = SLAConfig
        fields = ["priority", "response_minutes", "resolve_minutes"]
