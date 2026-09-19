import re

from django import forms

from .models import Booking, Destination


class BookingForm(forms.ModelForm):
    class Meta:
        model = Booking
        fields = ("first_name", "last_name", "phone", "destination")
        widgets = {
            "first_name": forms.TextInput(attrs={"autocomplete": "given-name"}),
            "last_name": forms.TextInput(attrs={"autocomplete": "family-name"}),
            "phone": forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel", "placeholder": "+998 90 123 45 67"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        destination = self.fields["destination"]
        destination.queryset = Destination.objects.published().only("id", "name")
        destination.empty_label = "Yo'nalishni tanlang"

    def clean_phone(self) -> str:
        """`90 123 45 67`, `+998901234567` va boshqa yozuvlarni `+998901234567` ga keltiradi."""
        digits = re.sub(r"\D", "", self.cleaned_data["phone"])
        if len(digits) == 9:  # mahalliy raqam, davlat kodisiz
            digits = "998" + digits
        if digits.startswith("998") and len(digits) != 12 or not 9 <= len(digits) <= 15:
            raise forms.ValidationError("Telefon raqamni to'g'ri kiriting, masalan: +998 90 123 45 67.")
        return "+" + digits
