import uuid
from datetime import timedelta

from django.conf import settings
from django.db import models
from django.utils import timezone


class RefreshTokenQuerySet(models.QuerySet):
    def active(self):
        return self.filter(revoked_at__isnull=True, expires_at__gt=timezone.now())


class RefreshToken(models.Model):
    """Serverda saqlanadigan refresh tokenlar (rotatsiya va bekor qilish uchun).

    JWT'ning o'zi bazada saqlanmaydi — faqat `jti` identifikatori va holati.
    Bitta login sessiyasidagi barcha tokenlar umumiy `family` ga ega bo'ladi:
    eski token qayta ishlatilsa, butun oila bekor qilinadi.
    """

    jti = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    family = models.UUIDField(db_index=True, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="refresh_tokens")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    revoked_at = models.DateTimeField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, blank=True)
    ip_address = models.GenericIPAddressField(null=True, blank=True)

    objects = RefreshTokenQuerySet.as_manager()

    class Meta:
        ordering = ["-created_at"]
        indexes = [models.Index(fields=["user", "revoked_at"])]
        verbose_name = "refresh token"
        verbose_name_plural = "refresh tokenlar"

    def __str__(self) -> str:
        return f"{self.user} · {self.jti}"

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= timezone.now()

    def was_rotated_within(self, seconds: int) -> bool:
        return self.revoked_at is not None and timezone.now() - self.revoked_at <= timedelta(seconds=seconds)
