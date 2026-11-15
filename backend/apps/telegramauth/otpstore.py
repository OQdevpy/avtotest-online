"""Redis ulanishi — Telegram kirish sessiyalari shu yerda TTL bilan saqlanadi.

Sessiya mantig'i ``verification`` modulida. Bazada faqat ``TelegramAccount``
bog'lanishi (telegram_id <-> phone <-> user, til) saqlanadi.
"""

from __future__ import annotations

import redis
from django.conf import settings

# Jarayon davomida bitta pool.
_client: redis.Redis | None = None


def client() -> redis.Redis:
    global _client
    if _client is None:
        url = getattr(settings, "REDIS_URL", "redis://localhost:6379/0")
        _client = redis.from_url(url, decode_responses=True)
    return _client
