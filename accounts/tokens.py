"""JWT (access + refresh) yaratish, tekshirish va rotatsiya qilish.

Oqim:
  * access  — qisqa muddatli (standart 15 daqiqa), faqat imzo bo'yicha tekshiriladi;
  * refresh — uzoq muddatli, bazadagi `RefreshToken` yozuvi bilan bog'langan;
    har safar ishlatilganda yangisiga almashtiriladi (rotation) va eski token
    qayta ishlatilsa butun oila bekor qilinadi (reuse detection).
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

import jwt
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import transaction
from django.http import HttpRequest
from django.utils import timezone

from .models import RefreshToken

ACCESS, REFRESH = "access", "refresh"


class TokenError(Exception):
    """Token yaroqsiz, muddati o'tgan yoki bekor qilingan."""


class TokenReuseError(TokenError):
    """Allaqachon almashtirilgan refresh token qayta ishlatildi."""

    def __init__(self, family: uuid.UUID):
        super().__init__("Refresh token qayta ishlatildi.")
        self.family = family


@dataclass(frozen=True)
class TokenPair:
    access: str
    refresh: str


def _cfg() -> dict:
    return settings.JWT


def _encode(payload: dict) -> str:
    return jwt.encode(payload, _cfg()["SIGNING_KEY"], algorithm=_cfg()["ALGORITHM"])


def decode(token: str, expected_type: str) -> dict:
    try:
        payload = jwt.decode(
            token,
            _cfg()["SIGNING_KEY"],
            algorithms=[_cfg()["ALGORITHM"]],
            options={"require": ["exp", "iat", "sub", "jti", "typ"]},
        )
    except jwt.PyJWTError as exc:
        raise TokenError(str(exc)) from exc
    if payload["typ"] != expected_type:
        raise TokenError("Token turi noto'g'ri.")
    return payload


def _claims(user_id: int, typ: str, ttl, jti: uuid.UUID, **extra) -> dict:
    now = timezone.now()
    return {"sub": str(user_id), "typ": typ, "jti": str(jti), "iat": now, "exp": now + ttl, **extra}


def make_access_token(user) -> str:
    return _encode(_claims(user.pk, ACCESS, _cfg()["ACCESS_TTL"], uuid.uuid4()))


def _client_meta(request: HttpRequest | None) -> dict:
    if request is None:
        return {}
    ip = request.META.get("REMOTE_ADDR")
    return {"user_agent": request.META.get("HTTP_USER_AGENT", "")[:255], "ip_address": ip or None}


def _issue(user, family: uuid.UUID, request: HttpRequest | None) -> TokenPair:
    ttl = _cfg()["REFRESH_TTL"]
    record = RefreshToken.objects.create(
        user=user, family=family, expires_at=timezone.now() + ttl, **_client_meta(request)
    )
    refresh = _encode(_claims(user.pk, REFRESH, ttl, record.jti, fam=str(family)))
    return TokenPair(access=make_access_token(user), refresh=refresh)


def issue_pair(user, request: HttpRequest | None = None) -> TokenPair:
    """Yangi login: yangi oila boshlaydi."""
    return _issue(user, uuid.uuid4(), request)


def rotate(refresh_token: str, request: HttpRequest | None = None) -> tuple[object, TokenPair | None]:
    """Refresh tokenni yangisiga almashtiradi.

    Qaytaradi `(user, pair)`. `pair` — `None` bo'lsa, foydalanuvchi shu so'rov uchun
    autentifikatsiya qilinadi, lekin yangi cookie berilmaydi (poyga holati: boshqa
    parallel so'rov allaqachon yangi juftlikni bergan).
    """
    try:
        with transaction.atomic():
            return _rotate(refresh_token, request)
    except TokenReuseError as exc:
        # Eski token qayta ishlatildi — o'g'irlangan bo'lishi mumkin: butun oilani bekor qilamiz.
        # (Tranzaksiyadan tashqarida, aks holda xatolik bilan birga qaytarib yuboriladi.)
        revoke_family(exc.family)
        raise


def _rotate(refresh_token: str, request: HttpRequest | None) -> tuple[object, TokenPair | None]:
    payload = decode(refresh_token, REFRESH)
    try:
        record = RefreshToken.objects.select_for_update().select_related("user").get(jti=payload["jti"])
    except RefreshToken.DoesNotExist as exc:
        raise TokenError("Refresh token topilmadi.") from exc

    if record.is_expired or not record.user.is_active:
        raise TokenError("Refresh token yaroqsiz.")

    if record.revoked_at is not None:
        if record.was_rotated_within(_cfg()["REUSE_GRACE_SECONDS"]):
            return record.user, None
        raise TokenReuseError(record.family)

    record.revoked_at = timezone.now()
    record.save(update_fields=["revoked_at"])
    return record.user, _issue(record.user, record.family, request)


def authenticate_access(token: str):
    """Access tokendan foydalanuvchini qaytaradi yoki `TokenError` ko'taradi."""
    payload = decode(token, ACCESS)
    user = get_user_model().objects.filter(pk=payload["sub"], is_active=True).first()
    if user is None:
        raise TokenError("Foydalanuvchi topilmadi.")
    return user


def revoke_family(family: uuid.UUID) -> int:
    return RefreshToken.objects.filter(family=family, revoked_at__isnull=True).update(revoked_at=timezone.now())


def revoke_refresh_token(token: str) -> None:
    """Chiqishda: token tegishli butun oilani bekor qiladi (yaroqsiz bo'lsa — jim o'tadi)."""
    try:
        payload = decode(token, REFRESH)
    except TokenError:
        return
    record = RefreshToken.objects.filter(jti=payload["jti"]).first()
    if record:
        revoke_family(record.family)


def revoke_all(user) -> int:
    return RefreshToken.objects.filter(user=user, revoked_at__isnull=True).update(revoked_at=timezone.now())
