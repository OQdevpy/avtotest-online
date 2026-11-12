"""Provayder kalitlarini bazada shifrlab saqlash.

AES-256-GCM; kalit `SECRET_KEY` dan HKDF-SHA256 bilan hosil qilinadi (alohida
sozlama yo'q). `SECRET_KEY` almashsa eski shifrlar ochilmaydi — kalitlar admin'dan
qayta kiritiladi (docs/DEPLOY.md).

Token: base64url(iv 12 B | shifr). Bo'sh matn — bo'sh token.
"""

import base64
import binascii
import os

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings

_INFO = b"payments-secrets"


def _key() -> bytes:
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=None, info=_INFO,
    ).derive(settings.SECRET_KEY.encode())


def encrypt(plain: str) -> str:
    if not plain:
        return ""
    iv = os.urandom(12)
    sealed = AESGCM(_key()).encrypt(iv, plain.encode(), None)
    return base64.urlsafe_b64encode(iv + sealed).decode()


def decrypt(token: str) -> str:
    """Ochib bo'lmasa (buzilgan yoki boshqa SECRET_KEY) — bo'sh satr."""
    if not token:
        return ""
    try:
        raw = base64.urlsafe_b64decode(token.encode())
        return AESGCM(_key()).decrypt(raw[:12], raw[12:], None).decode()
    except (InvalidTag, ValueError, binascii.Error):
        return ""
