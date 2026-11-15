"""So'rov yuborgan mijozning IP manzili."""


def client_ip(request) -> str:
    """nginx `X-Real-IP` ni `$remote_addr` bilan yozadi; `X-Forwarded-For` ga ishonilmaydi."""
    return (request.META.get("HTTP_X_REAL_IP") or request.META.get("REMOTE_ADDR") or "").strip()
