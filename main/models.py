import secrets

from django.conf import settings
from django.db import models
from django.db.models.functions import Substr
from django.urls import reverse
from django.utils.text import slugify

REFERENCE_ALPHABET = "ABCDEFGHJKMNPQRSTUVWXYZ23456789"  # 0/O, 1/I/L aralashmasin


def generate_reference() -> str:
    return "OL-" + "".join(secrets.choice(REFERENCE_ALPHABET) for _ in range(6))


class DestinationQuerySet(models.QuerySet):
    def published(self):
        return self.filter(is_published=True)

    def for_cards(self):
        """Kartochkalar uchun yengil so'rov: uzun tavsifning faqat boshini oladi."""
        return self.defer("description").annotate(
            excerpt=Substr("description", 1, 220)
        )


class Destination(models.Model):
    name = models.CharField("Nomi", max_length=100)
    slug = models.SlugField(max_length=120, unique=True, blank=True)
    image = models.ImageField("Asosiy rasm", upload_to="destinations/")
    description = models.TextField("Tavsif")
    price = models.PositiveIntegerField("Narxi")
    is_published = models.BooleanField("Saytda ko'rinsin", default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = DestinationQuerySet.as_manager()

    class Meta:
        ordering = ["id"]
        verbose_name = "yo'nalish"
        verbose_name_plural = "yo'nalishlar"

    def __str__(self) -> str:
        return self.display_name

    @property
    def display_name(self) -> str:
        """`BRAZILIA` kabi to'liq bosh harfli nomlarni `Brazilia` ko'rinishiga keltiradi."""
        return self.name.capitalize() if self.name.isupper() and len(self.name) > 3 else self.name

    def get_absolute_url(self) -> str:
        return reverse("main:destination_detail", args=[self.slug])

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = self._unique_slug()
        super().save(*args, **kwargs)

    def _unique_slug(self) -> str:
        base = slugify(self.name) or "yonalish"
        slug, n = base, 2
        while Destination.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug, n = f"{base}-{n}", n + 1
        return slug


class DestinationPhoto(models.Model):
    destination = models.ForeignKey(Destination, on_delete=models.CASCADE, related_name="photos")
    image = models.ImageField("Rasm", upload_to="destinations/gallery/")

    class Meta:
        ordering = ["id"]
        verbose_name = "yo'nalish rasmi"
        verbose_name_plural = "yo'nalish rasmlari"

    def __str__(self) -> str:
        return f"{self.destination} #{self.pk}"


class Booking(models.Model):
    class Status(models.TextChoices):
        NEW = "new", "Yangi"
        CONFIRMED = "confirmed", "Tasdiqlangan"
        CANCELLED = "cancelled", "Bekor qilingan"

    reference = models.CharField(max_length=12, unique=True, default=generate_reference, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="bookings"
    )
    first_name = models.CharField("Ism", max_length=100)
    last_name = models.CharField("Familiya", max_length=100)
    phone = models.CharField("Telefon raqam", max_length=20)
    destination = models.ForeignKey(
        Destination, on_delete=models.PROTECT, related_name="bookings", verbose_name="Yo'nalish"
    )
    status = models.CharField(max_length=10, choices=Status.choices, default=Status.NEW, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "bron"
        verbose_name_plural = "bronlar"

    def __str__(self) -> str:
        return f"{self.reference} — {self.first_name} {self.last_name}"

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    def get_absolute_url(self) -> str:
        return reverse("main:booking_done", args=[self.reference])
