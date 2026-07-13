from django import forms
from .models import Ticket

class TicketForm(forms.ModelForm):
    class Meta:
        model = Ticket
        fields = ("title", "description")
        widgets = {
            "title": forms.TextInput(attrs={"class": "form-control", "maxlength": 200}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": 6, "maxlength": 5000}),
        }

    def clean_title(self):
        value = self.cleaned_data["title"].strip()
        if len(value) < 5:
            raise forms.ValidationError("El título debe tener al menos 5 caracteres.")
        return value

    def clean_description(self):
        value = self.cleaned_data["description"].strip()
        if len(value) < 10:
            raise forms.ValidationError("La descripción debe tener al menos 10 caracteres.")
        return value
