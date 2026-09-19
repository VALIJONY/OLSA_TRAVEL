from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from accounts.models import RefreshToken


class Command(BaseCommand):
    help = "Muddati o'tgan va bekor qilingan refresh tokenlarni bazadan o'chiradi."

    def add_arguments(self, parser):
        parser.add_argument("--keep-days", type=int, default=7, help="Bekor qilingan yozuvlarni saqlash muddati.")

    def handle(self, *args, keep_days, **options):
        now = timezone.now()
        deleted, _ = RefreshToken.objects.filter(
            Q(expires_at__lt=now) | Q(revoked_at__lt=now - timedelta(days=keep_days))
        ).delete()
        self.stdout.write(self.style.SUCCESS(f"{deleted} ta token o'chirildi."))
