import shutil
import tempfile
from io import BytesIO

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase, override_settings
from django.urls import reverse
from PIL import Image

from .models import Booking, Destination, DestinationPhoto

MEDIA = tempfile.mkdtemp()


def make_image(name="flag.png", size=(64, 40)):
    buf = BytesIO()
    Image.new("RGB", size, "#bb9832").save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@override_settings(MEDIA_ROOT=MEDIA)
class BaseTest(TestCase):
    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA, ignore_errors=True)

    def setUp(self):
        cache.clear()
        self.brazil = Destination.objects.create(name="BRAZILIA", image=make_image(), description="Rio [1] de Janeiro.", price=120000)
        self.korea = Destination.objects.create(name="Korea", image=make_image("k.png"), description="Seoul", price=150000)
        self.hidden = Destination.objects.create(name="Secret", image=make_image("s.png"), description="-", price=1, is_published=False)


class ModelTests(BaseTest):
    def test_slug_is_unique_and_display_name_is_normalized(self):
        again = Destination.objects.create(name="Korea", image=make_image("k2.png"), description="x", price=1)
        self.assertEqual((self.brazil.slug, self.korea.slug, again.slug), ("brazilia", "korea", "korea-2"))
        self.assertEqual(self.brazil.display_name, "Brazilia")

    def test_booking_reference_is_generated_and_unique(self):
        refs = {Booking.objects.create(first_name="A", last_name="B", phone="+998901234567", destination=self.korea).reference for _ in range(20)}
        self.assertEqual(len(refs), 20)
        self.assertTrue(all(r.startswith("OL-") and len(r) == 9 for r in refs))


class PageTests(BaseTest):
    def test_public_pages_render(self):
        for name, args in [("main:home", []), ("main:destination_list", []), ("main:about", []), ("main:booking", []),
                           ("main:destination_detail", [self.brazil.slug]), ("accounts:login", []), ("accounts:register", [])]:
            with self.subTest(name):
                self.assertEqual(self.client.get(reverse(name, args=args)).status_code, 200)

    def test_unpublished_destination_is_hidden_everywhere(self):
        self.assertEqual(self.client.get(reverse("main:destination_detail", args=[self.hidden.slug])).status_code, 404)
        self.assertNotContains(self.client.get(reverse("main:home")), "Secret")
        self.assertNotContains(self.client.get(reverse("main:destination_list")), "Secret")

    def test_search_and_sort(self):
        response = self.client.get(reverse("main:destination_list"), {"q": "brazil"})
        self.assertEqual([d.pk for d in response.context_data["destinations"]], [self.brazil.pk])
        response = self.client.get(reverse("main:destination_list"), {"sort": "-price"})
        self.assertEqual([d.pk for d in response.context_data["destinations"]], [self.korea.pk, self.brazil.pk])

    def test_empty_search_shows_helpful_message(self):
        self.assertContains(self.client.get(reverse("main:destination_list"), {"q": "zzz"}), "topilmadi")

    def test_list_uses_constant_number_of_queries(self):
        for i in range(10):
            Destination.objects.create(name=f"C{i}", image=make_image(f"{i}.png"), description="d" * 500, price=i)
        with self.assertNumQueries(2):  # count + sahifa
            self.client.get(reverse("main:destination_list"))

    def test_detail_lists_photos_without_n_plus_one(self):
        for i in range(4):
            DestinationPhoto.objects.create(destination=self.brazil, image=make_image(f"p{i}.png"))
        with self.assertNumQueries(3):  # yo'nalish + suratlar + tegishli yo'nalishlar
            response = self.client.get(reverse("main:destination_detail", args=[self.brazil.slug]))
        self.assertContains(response, "<div id=\"photo-", count=4)

    def test_footnote_markers_are_stripped(self):
        self.assertNotContains(self.client.get(reverse("main:destination_detail", args=[self.brazil.slug])), "[1]")


class BookingTests(BaseTest):
    data = {"first_name": "Vali", "last_name": "Do'sov", "phone": "90 123 45 67"}

    def post(self, **extra):
        return self.client.post(reverse("main:booking"), {**self.data, "destination": self.korea.pk, **extra})

    def test_valid_booking_is_saved_with_normalized_phone_and_redirects(self):
        response = self.post()
        booking = Booking.objects.get()
        self.assertEqual(booking.phone, "+998901234567")
        self.assertIsNone(booking.user)
        self.assertRedirects(response, booking.get_absolute_url())
        self.assertContains(self.client.get(booking.get_absolute_url()), booking.reference)

    def test_invalid_phone_is_rejected(self):
        response = self.post(phone="123")
        self.assertEqual(Booking.objects.count(), 0)
        self.assertContains(response, "Telefon raqamni to&#39;g&#39;ri kiriting")

    def test_unpublished_destination_cannot_be_booked(self):
        self.post(destination=self.hidden.pk)
        self.assertEqual(Booking.objects.count(), 0)

    def test_destination_is_preselected_from_query(self):
        response = self.client.get(reverse("main:booking"), {"destination": self.korea.slug})
        self.assertEqual(response.context_data["selected"], self.korea)

    def test_logged_in_user_is_attached_and_prefilled(self):
        user = get_user_model().objects.create_user("ali", password="s3cret-pass!", first_name="Ali", last_name="Valiyev")
        self.client.post(reverse("accounts:login"), {"username": "ali", "password": "s3cret-pass!"})
        self.assertEqual(self.client.get(reverse("main:booking")).context_data["form"].initial["first_name"], "Ali")
        self.post()
        self.assertEqual(Booking.objects.get().user, user)
        self.assertContains(self.client.get(reverse("accounts:profile")), Booking.objects.get().reference)

    def test_booking_is_throttled_per_ip(self):
        for _ in range(5):
            self.post()
        response = self.post()
        self.assertEqual(Booking.objects.count(), 5)
        self.assertContains(response, "juda ko")

    def test_unknown_reference_is_404(self):
        self.assertEqual(self.client.get(reverse("main:booking_done", args=["OL-NOPE00"])).status_code, 404)
