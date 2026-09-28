from django import forms

from .models import GuestbookEntry


class GuestbookEntryForm(forms.ModelForm):
    class Meta:
        model = GuestbookEntry
        fields = ["name", "message"]
        widgets = {
            "name": forms.TextInput(attrs={
                "class": "form-input",
                "placeholder": "Your name",
                "autocomplete": "name",
            }),
            "message": forms.Textarea(attrs={
                "class": "form-input form-textarea",
                "placeholder": "Leave a message",
                "rows": 4,
            }),
        }
