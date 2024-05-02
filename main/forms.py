from django import forms
from main.models import select

class SelectRegistrForm(forms.ModelForm):
    class Meta:
        model = select
        fields = ('Ism', 'Familiya', 'Telefon_raqam', 'Sayohat_joyini_tanlang')
