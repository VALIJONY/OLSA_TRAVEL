"""Har bir so'rovda `request.user` ni JWT cookie'lardan aniqlaydi.

1. Access token yaroqli bo'lsa — foydalanuvchi bazadan kerak bo'lganda (lazy) olinadi.
2. Access yo'q/eskirgan bo'lsa, lekin refresh yaroqli bo'lsa — token juftligi
   avtomatik yangilanadi va yangi cookie'lar javobga yoziladi. Brauzer tomonida
   JavaScript kerak emas.
3. Ikkalasi ham yaroqsiz bo'lsa — cookie'lar tozalanadi.

Admin paneli o'zining sessiya autentifikatsiyasida qoladi: cookie'lar bo'lmasa
`request.user` ga tegilmaydi.
"""

from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from django.utils.cache import patch_vary_headers
from django.utils.functional import SimpleLazyObject

from . import tokens
from .auth import clear_auth_cookies, set_auth_cookies


def _lazy_user(user_id: str):
    def load():
        return get_user_model().objects.filter(pk=user_id, is_active=True).first() or AnonymousUser()

    return SimpleLazyObject(load)


class JWTAuthenticationMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        request.jwt_pair = None
        request.jwt_clear = False
        self._authenticate(request)

        response = self.get_response(request)

        if request.jwt_pair:
            set_auth_cookies(response, request.jwt_pair)
        elif request.jwt_clear:
            clear_auth_cookies(response)
        patch_vary_headers(response, ("Cookie",))
        return response

    @staticmethod
    def _authenticate(request) -> None:
        cfg = settings.JWT
        access = request.COOKIES.get(cfg["ACCESS_COOKIE"])
        refresh = request.COOKIES.get(cfg["REFRESH_COOKIE"])
        if not (access or refresh):
            return

        if access:
            try:
                request.user = _lazy_user(tokens.decode(access, tokens.ACCESS)["sub"])
                return
            except tokens.TokenError:
                pass  # eskirgan yoki soxta — refresh bilan urinib ko'ramiz

        if refresh:
            try:
                request.user, request.jwt_pair = tokens.rotate(refresh, request)
                return
            except tokens.TokenError:
                pass

        request.user = AnonymousUser()
        request.jwt_clear = True
