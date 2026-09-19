from django.core.management.base import BaseCommand

from main.models import Destination, DestinationPhoto
from main.thumbs import WIDTHS, thumb_url


class Command(BaseCommand):
    help = "Barcha rasmlar uchun kichraytirilgan WebP nusxalarni oldindan yaratadi."

    def handle(self, *args, **options):
        images = [d.image for d in Destination.objects.all()] + [p.image for p in DestinationPhoto.objects.all()]
        for image in images:
            for width in WIDTHS:
                thumb_url(image, width)
        self.stdout.write(self.style.SUCCESS(f"{len(images)} ta rasm × {len(WIDTHS)} o'lcham tayyor."))
