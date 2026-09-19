from django.conf import settings
from django.contrib import messages
from django.db.models import Q
from django.views.generic import CreateView, DetailView, ListView, TemplateView

from config import throttle

from .forms import BookingForm
from .models import Booking, Destination

BOOKING_LIMIT, BOOKING_WINDOW = 5, 60 * 60


class HomeView(TemplateView):
    template_name = "main/home.html"

    def get_context_data(self, **kwargs):
        destinations = list(Destination.objects.published().for_cards())
        return super().get_context_data(destinations=destinations, **kwargs)


class DestinationListView(ListView):
    template_name = "main/destination_list.html"
    context_object_name = "destinations"
    paginate_by = settings.DESTINATIONS_PER_PAGE
    paginate_orphans = 2

    SORTS = {
        "new": ("Yangilari", "-id"),
        "price": ("Arzonlari", "price"),
        "-price": ("Qimmatlari", "-price"),
        "name": ("Nomi bo'yicha", "name"),
    }

    def get_queryset(self):
        qs = Destination.objects.published().for_cards()
        if q := self.request.GET.get("q", "").strip()[:80]:
            qs = qs.filter(Q(name__icontains=q) | Q(description__icontains=q))
        return qs.order_by(self.SORTS.get(self.request.GET.get("sort"), self.SORTS["new"])[1])

    def get_context_data(self, **kwargs):
        params = self.request.GET.copy()
        params.pop("page", None)
        return super().get_context_data(
            q=self.request.GET.get("q", "").strip()[:80],
            sort=self.request.GET.get("sort") if self.request.GET.get("sort") in self.SORTS else "new",
            sorts={key: label for key, (label, _) in self.SORTS.items()},
            query=params.urlencode(),
            **kwargs,
        )


class DestinationDetailView(DetailView):
    template_name = "main/destination_detail.html"
    context_object_name = "destination"

    def get_queryset(self):
        return Destination.objects.published().prefetch_related("photos")

    def get_context_data(self, **kwargs):
        related = Destination.objects.published().for_cards().exclude(pk=self.object.pk)[:3]
        return super().get_context_data(related=related, **kwargs)


class BookingCreateView(CreateView):
    template_name = "main/booking_form.html"
    form_class = BookingForm

    def get_initial(self):
        initial = {}
        user = self.request.user
        if user.is_authenticated:
            initial["first_name"] = user.first_name
            initial["last_name"] = user.last_name
        if slug := self.request.GET.get("destination"):
            initial["destination"] = Destination.objects.published().filter(slug=slug).values_list("pk", flat=True).first()
        return initial

    def get_context_data(self, **kwargs):
        form = kwargs.get("form") or self.get_form()
        try:
            selected = Destination.objects.published().filter(pk=form["destination"].value() or None).first()
        except (ValueError, TypeError):
            selected = None
        return super().get_context_data(selected=selected, **kwargs)

    def post(self, request, *args, **kwargs):
        if throttle.is_blocked("booking", throttle.client_ip(request), BOOKING_LIMIT):
            messages.error(request, "Bir soat ichida juda ko'p bron yuborildi. Keyinroq qayta urinib ko'ring.")
            return self.get(request, *args, **kwargs)
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        if self.request.user.is_authenticated:
            form.instance.user = self.request.user
        throttle.register("booking", throttle.client_ip(self.request), BOOKING_WINDOW)
        return super().form_valid(form)  # get_absolute_url() ga yo'naltiradi


class BookingDoneView(DetailView):
    template_name = "main/booking_done.html"
    slug_field = "reference"
    slug_url_kwarg = "reference"
    context_object_name = "booking"

    def get_queryset(self):
        return Booking.objects.select_related("destination")



class AboutView(TemplateView):
    template_name = "main/about.html"

    def get_context_data(self, **kwargs):
        return super().get_context_data(
            destination_count=Destination.objects.published().count(), **kwargs
        )
