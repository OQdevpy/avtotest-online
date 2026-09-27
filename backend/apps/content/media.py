"""Savol rasmlari va audiosi.

Rasmlar har doim WebP'da saqlanadi — mobil ilova va web bir xil formatni
kutadi, hajmi ham kichik. Fayl nomiga qisqa tasodifiy qo'shimcha qo'shiladi,
shuning uchun rasm almashtirilganda mijozdagi kesh yangilanadi.
"""

import secrets
from pathlib import Path

from django.conf import settings
from PIL import Image, UnidentifiedImageError

IMAGE_DIR = "images"
AUDIO_DIR = "audio"
WEBP_QUALITY = 85
AUDIO_EXTENSIONS = {".mp3", ".m4a", ".aac", ".ogg", ".wav"}


class UnreadableImage(Exception):
    """Fayl rasm emas yoki ochib bo'lmaydi."""


class UnsupportedAudio(Exception):
    """Audio kengaytmasi qo'llab-quvvatlanmaydi."""


def media_path(relative: str) -> Path:
    return Path(settings.MEDIA_ROOT) / relative


def unique_name(stem: str) -> str:
    """Kesh yangilanishi uchun nomga qisqa tasodifiy qo'shimcha."""
    return f"{stem}_{secrets.token_hex(3)}"


def to_webp(source, dest_stem: str) -> str:
    """Rasmni WebP qilib `media/images/` ga yozadi va nisbiy yo'lni qaytaradi."""
    target_dir = media_path(IMAGE_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    relative = f"{IMAGE_DIR}/{dest_stem}.webp"
    try:
        with Image.open(source) as image:
            image.convert("RGB").save(media_path(relative), "WEBP", quality=WEBP_QUALITY)
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise UnreadableImage("Faylni rasm sifatida o'qib bo'lmadi.") from exc
    return relative


def save_audio(source, dest_stem: str, original_name: str) -> str:
    """Audio faylni `media/audio/` ga yozadi va nisbiy yo'lni qaytaradi."""
    extension = Path(original_name).suffix.lower()
    if extension not in AUDIO_EXTENSIONS:
        raise UnsupportedAudio(
            f"Qo'llab-quvvatlanadigan kengaytmalar: {', '.join(sorted(AUDIO_EXTENSIONS))}"
        )
    target_dir = media_path(AUDIO_DIR)
    target_dir.mkdir(parents=True, exist_ok=True)
    relative = f"{AUDIO_DIR}/{dest_stem}{extension}"
    with media_path(relative).open("wb") as handle:
        for chunk in source.chunks():
            handle.write(chunk)
    return relative


def remove_quietly(relative: str) -> None:
    """Eski faylni o'chiradi; yo'q bo'lsa jim o'tadi."""
    if not relative:
        return
    try:
        media_path(relative).unlink(missing_ok=True)
    except OSError:
        pass
