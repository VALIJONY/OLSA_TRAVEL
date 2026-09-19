from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm


class LoginForm(AuthenticationForm):
    error_messages = {
        "invalid_login": "Foydalanuvchi nomi yoki parol noto'g'ri.",
        "inactive": "Bu hisob faol emas.",
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].label = "Foydalanuvchi nomi"
        self.fields["password"].label = "Parol"
        self.fields["username"].widget.attrs.update(autocomplete="username", autofocus=True)
        self.fields["password"].widget.attrs.update(autocomplete="current-password")


class RegisterForm(UserCreationForm):
    email = forms.EmailField(label="Elektron pochta", required=False)

    class Meta(UserCreationForm.Meta):
        model = get_user_model()
        fields = ("username", "first_name", "email")
        labels = {"username": "Foydalanuvchi nomi", "first_name": "Ismingiz"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["password1"].label = "Parol"
        self.fields["password2"].label = "Parolni takrorlang"
        self.fields["first_name"].required = True
        self.fields["username"].help_text = "Harflar, raqamlar va @/./+/-/_ belgilari."
        self.fields["username"].widget.attrs.update(autocomplete="username")
        self.fields["password1"].widget.attrs.update(autocomplete="new-password")
        self.fields["password2"].widget.attrs.update(autocomplete="new-password")
