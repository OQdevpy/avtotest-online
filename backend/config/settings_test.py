"""Sinov sozlamalari.

Loyiha `DATABASE_URL` ni majburiy qiladi va `DEBUG=False` da `SECRET_KEY` talab
qiladi. Bu modul testlar uchun ularni o'rnatadi, so'ng asosiy sozlamalarni
import qiladi. Testlar tezligi uchun sqlite; produksiya Postgres'da qoladi.
"""

import os

os.environ.setdefault("DATABASE_URL", "sqlite:///test-db.sqlite3")
os.environ.setdefault("DEBUG", "1")
os.environ.setdefault("SECRET_KEY", "test-only-key-" + "x" * 32)

from config.settings import *  # noqa: E402,F401,F403

# Parol hash'i testlarda sekin — eng arzon algoritm yetarli.
PASSWORD_HASHERS = ["django.contrib.auth.hashers.MD5PasswordHasher"]
