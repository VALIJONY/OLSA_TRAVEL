from django.conf import settings
from django.contrib import messages
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseNotAllowed, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views import View
from django.views.generic import FormView, TemplateView

from config import throttle
from main.models import Booking

from .auth import login_user, logout_user
from .forms import LoginForm, RegisterForm

LOGIN_ATTEMPTS, LOGIN_WINDOW = 5, 15 * 60


class NextUrlMixin:
    """`?next=` / `next` maydonini xavfsiz tekshiradi (open redirect'dan himoya)."""

    def get_next_url(self) -> str:
        candidate = self.request.POST.get("next") or self.request.GET.get("next", "")
        if candidate and url_has_allowed_host_and_scheme(
            candidate, allowed_hosts={self.request.get_host()}, require_https=self.request.is_secure()
        ):
            return candidate
        return ""

    def get_context_data(self, **kwargs):
        return super().get_context_data(next=self.get_next_url(), **kwargs)


class AnonymousOnlyMixin:
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            return redirect(settings.LOGIN_REDIRECT_URL)
        return super().dispatch(request, *args, **kwargs)


class LoginView(AnonymousOnlyMixin, NextUrlMixin, FormView):
    template_name = "accounts/login.html"
    form_class = LoginForm

    def get_form_kwargs(self):
        return {**super().get_form_kwargs(), "request": self.request}

    def _throttle_id(self, form) -> str:
        return f"{throttle.client_ip(self.request)}:{form.data.get('username', '').lower()}"

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        if throttle.is_blocked("login", self._throttle_id(form), LOGIN_ATTEMPTS):
            form.add_error(None, "Urinishlar juda ko'p. Bir necha daqiqadan keyin qayta urinib ko'ring.")
            return self.form_invalid(form)
        return self.form_valid(form) if form.is_valid() else self.form_invalid(form)

    def form_valid(self, form):
        throttle.reset("login", self._throttle_id(form))
        login_user(self.request, form.get_user())
        messages.success(self.request, f"Xush kelibsiz, {form.get_user().first_name or form.get_user().username}!")
        return HttpResponseRedirect(self.get_next_url() or reverse(settings.LOGIN_REDIRECT_URL))

    def form_invalid(self, form):
        if form.errors:
            throttle.register("login", self._throttle_id(form), LOGIN_WINDOW)
        return super().form_invalid(form)


class RegisterView(AnonymousOnlyMixin, NextUrlMixin, FormView):
    template_name = "accounts/register.html"
    form_class = RegisterForm

    def form_valid(self, form):
        user = form.save()
        login_user(self.request, user)
        messages.success(self.request, "Hisob yaratildi. Sayohatni rejalashtirishni boshlang!")
        return HttpResponseRedirect(self.get_next_url() or reverse("main:destination_list"))


class LogoutView(View):
    """Faqat POST (CSRF bilan): GET orqali tasodifan chiqib ketishning oldini oladi."""

    def get(self, request):
        return HttpResponseNotAllowed(["POST"])

    def post(self, request):
        logout_user(request, everywhere=bool(request.POST.get("everywhere")))
        messages.info(request, "Hisobdan chiqdingiz.")
        return redirect("main:home")


class ProfileView(LoginRequiredMixin, TemplateView):
    template_name = "accounts/profile.html"

    def get_context_data(self, **kwargs):
        bookings = Booking.objects.filter(user=self.request.user).select_related("destination")
        return super().get_context_data(bookings=bookings, **kwargs)
