"""Oddiy kesh asosidagi tezlik cheklovi (login urinishlari, bron spami)."""

from django.core.cache import cache
from django.http import HttpRequest


def client_ip(request: HttpRequest) -> str:
    return request.META.get("REMOTE_ADDR", "unknown")


def _key(scope: str, ident: str) -> str:
    return f"throttle:{scope}:{ident}"


def is_blocked(scope: str, ident: str, limit: int) -> bool:
    return cache.get(_key(scope, ident), 0) >= limit


def register(scope: str, ident: str, window: int) -> None:
    key = _key(scope, ident)
    if cache.add(key, 1, window):
        return
    try:
        cache.incr(key)
    except ValueError:  # kalit shu orada muddati o'tib ketdi
        cache.set(key, 1, window)


def reset(scope: str, ident: str) -> None:
    cache.delete(_key(scope, ident))
