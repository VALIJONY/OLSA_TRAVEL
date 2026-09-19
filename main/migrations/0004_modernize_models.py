"""Modellarni toza inglizcha nomlarga o'tkazadi, mavjud ma'lumotlarni saqlagan holda.

gallery         -> Destination
CountryPictures -> DestinationPhoto
select          -> Booking
logotip         -> o'chiriladi (ishlatilmagan)
"""

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models
from django.utils.text import slugify

import main.models


def fill_slugs(apps, schema_editor):
    Destination = apps.get_model("main", "Destination")
    taken = set()
    for obj in Destination.objects.order_by("id"):
        base = slugify(obj.name) or "yonalish"
        slug, n = base, 2
        while slug in taken:
            slug, n = f"{base}-{n}", n + 1
        taken.add(slug)
        obj.slug = slug
        obj.save(update_fields=["slug"])


def fill_references(apps, schema_editor):
    Booking = apps.get_model("main", "Booking")
    taken = set()
    for obj in Booking.objects.all():
        ref = main.models.generate_reference()
        while ref in taken:
            ref = main.models.generate_reference()
        taken.add(ref)
        obj.reference = ref
        obj.save(update_fields=["reference"])


class Migration(migrations.Migration):
    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("main", "0003_countrypictures"),
    ]

    operations = [
        migrations.DeleteModel(name="logotip"),
        # --- gallery -> Destination -------------------------------------------
        migrations.RenameModel(old_name="gallery", new_name="Destination"),
        migrations.RenameField("Destination", "Davlat", "name"),
        migrations.RenameField("Destination", "rasm", "image"),
        migrations.RenameField("Destination", "malumot", "description"),
        migrations.RenameField("Destination", "narxi", "price"),
        migrations.AlterField("Destination", "name", models.CharField(max_length=100, verbose_name="Nomi")),
        migrations.AlterField(
            "Destination",
            "image",
            models.ImageField(upload_to="destinations/", verbose_name="Asosiy rasm"),
        ),
        migrations.AlterField("Destination", "description", models.TextField(verbose_name="Tavsif")),
        migrations.AlterField(
            "Destination", "price", models.PositiveIntegerField(verbose_name="Narxi")
        ),
        migrations.AddField(
            "Destination",
            "slug",
            models.SlugField(max_length=120, blank=True, null=True),
        ),
        migrations.AddField(
            "Destination",
            "is_published",
            models.BooleanField(default=True, verbose_name="Saytda ko'rinsin"),
        ),
        migrations.AddField(
            "Destination",
            "created_at",
            models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.RunPython(fill_slugs, migrations.RunPython.noop),
        migrations.AlterField(
            "Destination", "slug", models.SlugField(max_length=120, unique=True, blank=True)
        ),
        migrations.AlterModelOptions(
            "Destination",
            options={
                "ordering": ["id"],
                "verbose_name": "yo'nalish",
                "verbose_name_plural": "yo'nalishlar",
            },
        ),
        # --- CountryPictures -> DestinationPhoto ------------------------------
        migrations.RenameModel(old_name="CountryPictures", new_name="DestinationPhoto"),
        migrations.RenameField("DestinationPhoto", "picture", "image"),
        migrations.RenameField("DestinationPhoto", "country_id", "destination"),
        migrations.AlterField(
            "DestinationPhoto",
            "image",
            models.ImageField(upload_to="destinations/gallery/", verbose_name="Rasm"),
        ),
        migrations.AlterField(
            "DestinationPhoto",
            "destination",
            models.ForeignKey(
                on_delete=django.db.models.deletion.CASCADE,
                related_name="photos",
                to="main.destination",
            ),
        ),
        migrations.AlterModelOptions(
            "DestinationPhoto",
            options={
                "ordering": ["id"],
                "verbose_name": "yo'nalish rasmi",
                "verbose_name_plural": "yo'nalish rasmlari",
            },
        ),
        # --- select -> Booking -------------------------------------------------
        migrations.RenameModel(old_name="select", new_name="Booking"),
        migrations.RenameField("Booking", "Ism", "first_name"),
        migrations.RenameField("Booking", "Familiya", "last_name"),
        migrations.RenameField("Booking", "Telefon_raqam", "phone"),
        migrations.RenameField("Booking", "Sayohat_joyini_tanlang", "destination"),
        migrations.AlterField(
            "Booking", "first_name", models.CharField(max_length=100, verbose_name="Ism")
        ),
        migrations.AlterField(
            "Booking", "last_name", models.CharField(max_length=100, verbose_name="Familiya")
        ),
        migrations.AlterField(
            "Booking", "phone", models.CharField(max_length=20, verbose_name="Telefon raqam")
        ),
        migrations.AlterField(
            "Booking",
            "destination",
            models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="bookings",
                to="main.destination",
                verbose_name="Yo'nalish",
            ),
        ),
        migrations.AddField(
            "Booking",
            "reference",
            models.CharField(max_length=12, null=True, editable=False),
        ),
        migrations.AddField(
            "Booking",
            "user",
            models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="bookings",
                to=settings.AUTH_USER_MODEL,
            ),
        ),
        migrations.AddField(
            "Booking",
            "status",
            models.CharField(
                choices=[("new", "Yangi"), ("confirmed", "Tasdiqlangan"), ("cancelled", "Bekor qilingan")],
                db_index=True,
                default="new",
                max_length=10,
            ),
        ),
        migrations.AddField(
            "Booking",
            "created_at",
            models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.RunPython(fill_references, migrations.RunPython.noop),
        migrations.AlterField(
            "Booking",
            "reference",
            models.CharField(
                default=main.models.generate_reference, editable=False, max_length=12, unique=True
            ),
        ),
        migrations.AlterModelOptions(
            "Booking",
            options={
                "ordering": ["-created_at"],
                "verbose_name": "bron",
                "verbose_name_plural": "bronlar",
            },
        ),
    ]
