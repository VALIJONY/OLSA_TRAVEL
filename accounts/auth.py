"""View'lar uchun JWT login/logout yordamchilari.

Cookie'larni o'zi yozmaydi — faqat `request` ga belgi qo'yadi;
javobga yozish `JWTAuthenticationMiddleware` zimmasida.
"""

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpRequest, HttpResponse

from . import tokens


def login_user(request: HttpRequest, user) -> None:
    request.user = user
    request.jwt_pair = tokens.issue_pair(user, request)
    request.jwt_clear = False


def logout_user(request: HttpRequest, everywhere: bool = False) -> None:
    user = request.user
    if everywhere and user.is_authenticated:
        tokens.revoke_all(user)
    elif (refresh := request.COOKIES.get(settings.JWT["REFRESH_COOKIE"])):
        tokens.revoke_refresh_token(refresh)
    request.user = AnonymousUser()
    request.jwt_pair = None
    request.jwt_clear = True


def set_auth_cookies(response: HttpResponse, pair: tokens.TokenPair) -> None:
    cfg = settings.JWT
    common = {"httponly": True, "secure": not settings.DEBUG, "samesite": "Lax", "path": "/"}
    response.set_cookie(cfg["ACCESS_COOKIE"], pair.access, max_age=int(cfg["ACCESS_TTL"].total_seconds()), **common)
    response.set_cookie(cfg["REFRESH_COOKIE"], pair.refresh, max_age=int(cfg["REFRESH_TTL"].total_seconds()), **common)


def clear_auth_cookies(response: HttpResponse) -> None:
    for name in (settings.JWT["ACCESS_COOKIE"], settings.JWT["REFRESH_COOKIE"]):
        response.delete_cookie(name, path="/", samesite="Lax")
