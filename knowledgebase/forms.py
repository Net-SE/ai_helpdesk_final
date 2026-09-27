from django import forms
from .models import KBArticle


class KBArticleForm(forms.ModelForm):
    class Meta:
        model = KBArticle
        fields = ["title", "body", "is_public"]
