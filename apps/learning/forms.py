from django import forms

from .models import LearningArticle


class LearningArticleForm(forms.ModelForm):
    class Meta:
        model = LearningArticle
        fields = ("category", "title", "summary", "body", "language")
        widgets = {
            "summary": forms.Textarea(attrs={"rows": 3}),
            "body": forms.Textarea(attrs={"rows": 12}),
        }
