"""Jinja2 muhiti: shablonlarda ishlatiladigan global funksiyalar va filtrlar."""

import re

from django.conf import settings
from django.contrib.messages import get_messages
from django.templatetags.static import static
from django.urls import reverse
from django.utils import timezone
from jinja2 import Environment
from jinja2.utils import markupsafe

from main.thumbs import srcset, thumb_url

_FOOTNOTE = re.compile(r"\[[^\]\s]{1,4}\]")  # Vikipediyadagi [a], [22] kabi havolalar


def url(name: str, *args, **kwargs) -> str:
    return reverse(name, args=args or None, kwargs=kwargs or None)


def price(value: int) -> str:
    """120000 -> `120 000 so'm` (bo'linmas bo'shliq bilan)."""
    return f"{int(value):,}".replace(",", " ") + f" {settings.CURRENCY_LABEL}"


def date(value) -> str:
    return timezone.localtime(value).strftime("%d.%m.%Y")


def excerpt(text: str, length: int = 140) -> str:
    text = " ".join(_FOOTNOTE.sub("", text or "").split())
    if len(text) <= length:
        return text
    return text[:length].rsplit(" ", 1)[0].rstrip(",.;:") + "…"


def paragraphs(text: str):
    """Matnni bo'sh qator bo'yicha xavfsiz <p> bloklariga ajratadi."""
    chunks = [c.strip() for c in _FOOTNOTE.sub("", text or "").replace("\r", "").split("\n") if c.strip()]
    return markupsafe.Markup("".join(f"<p>{markupsafe.escape(c)}</p>" for c in chunks))


def environment(**options) -> Environment:
    env = Environment(**options)
    env.globals.update(static=static, url=url, thumb=thumb_url, srcset=srcset, get_messages=get_messages)
    env.filters.update(price=price, excerpt=excerpt, paragraphs=paragraphs, date=date)
    env.trim_blocks = True
    env.lstrip_blocks = True
    return env
