"""Rasmlarni talab bo'yicha kichraytirib, WebP formatida `media_files/cache/` ga saqlaydi.

Asl fayl tegilmaydi. Kichik nusxa birinchi so'rovda yaratiladi va keyin diskdan beriladi.
Katta (4K, 6 MB) fon rasmlari o'rniga sahifaga 30–150 KB li nusxalar ketadi.
"""

from __future__ import annotations

import os
from pathlib import Path

from django.conf import settings
from PIL import Image, ImageOps

WIDTHS = (480, 800, 1280, 1920)
QUALITY = 78


def _cache_path(name: str, width: int) -> Path:
    return Path(settings.MEDIA_ROOT) / "cache" / str(width) / Path(name).with_suffix(".webp")


def _build(source: Path, target: Path, width: int) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as img:
        img = ImageOps.exif_transpose(img)
        if img.mode not in ("RGB", "RGBA"):
            img = img.convert("RGB")
        img.thumbnail((width, width * 4), Image.Resampling.LANCZOS)  # kattalashtirmaydi
        tmp = target.with_suffix(f".{os.getpid()}.tmp")
        img.save(tmp, "WEBP", quality=QUALITY, method=4)
    os.replace(tmp, target)


def thumb_url(image, width: int) -> str:
    """`ImageField` uchun `width` kenglikdagi WebP nusxasining URL manzili."""
    if not image:
        return ""
    source = Path(image.path)
    target = _cache_path(image.name, width)
    try:
        if not target.exists() or target.stat().st_mtime < source.stat().st_mtime:
            _build(source, target, width)
    except (OSError, ValueError):  # fayl yo'q yoki rasm buzilgan — aslini beramiz
        return image.url
    return f"{settings.MEDIA_URL}cache/{width}/{Path(image.name).with_suffix('.webp').as_posix()}"


def srcset(image, max_width: int = 1920) -> str:
    return ", ".join(f"{thumb_url(image, w)} {w}w" for w in WIDTHS if w <= max_width)
