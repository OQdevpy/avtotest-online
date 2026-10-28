"""Web ilovalar uchun shifrlangan kanal — `POST /api/v1/s/`.

Brauzerning Network oynasida endpoint, so'rov parametrlari, token va javoblar
ko'rinmasligi uchun web ilova barcha API so'rovlarini bitta shifrlangan
"konvert" ichida shu yerga yuboradi. Server konvertni ochadi, so'rovni odatdagi
view'ga ichkarida uzatadi va javobni shifrlab qaytaradi.

Kalit — ECDH (P-256) + HKDF-SHA256 → AES-256-GCM:
- Serverning doimiy kaliti `SECRET_KEY` dan hosil qilinadi (qo'shimcha sozlama
  yo'q, barcha gunicorn worker'larida bir xil). Ochiq qismi: `GET /api/v1/s/key/`.
- Brauzer har sahifa yuklanganda yangi, eksport qilib bo'lmaydigan kalit
  juftligini yaratadi va ochiq qismini har so'rov boshida yuboradi. Shuning
  uchun Network'ni ko'rgan odam (brauzerdagi maxfiy kalitsiz) ochib bo'lmaydi.

So'rov tanasi:  client_pub (65 B) | iv (12 B) | AES-GCM(json)
  json: {"m": metod, "p": "/content/version/", "q": {...}, "b": tana, "t": access token}
Javob tanasi:   iv (12 B) | AES-GCM(json)
  json: {"s": ichki status, "b": ichki javob tanasi}
Tashqi status doim 200 (xato ham shifrlangan ichida) — Network'dan hech narsa
bilinmaydi. Konvertni ochib bo'lmasa — 400, tanasiz.
"""

import base64
import hashlib
import io
import json
import logging
import os
import re
import time
from urllib.parse import urlencode

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from django.conf import settings
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponse, JsonResponse
from django.urls import Resolver404, resolve
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

logger = logging.getLogger(__name__)

API_PREFIX = "/api/v1"
HKDF_INFO = b"avtotest-web-v1"
PUBLIC_KEY_LEN = 65  # siqilmagan P-256 nuqtasi
IV_LEN = 12
MAX_BODY = 64 * 1024

# Web ilovalar ishlatadigan yo'llargina o'tkaziladi. Telefon+parol bilan kirish,
# shef (`manage/`) va boshqa API'lar bu kanal orqali ochilmaydi.
ALLOWED = (
    ("POST", re.compile(r"^/auth/login-code/$")),
    ("POST", re.compile(r"^/auth/token/refresh/$")),
    ("POST", re.compile(r"^/auth/logout/$")),
    ("GET", re.compile(r"^/content/version/$")),
    ("GET", re.compile(r"^/sections/$")),
    ("GET", re.compile(r"^/lessons/$")),
    ("GET", re.compile(r"^/questions/$")),
    ("GET", re.compile(r"^/tickets/$")),
    ("GET", re.compile(r"^/tickets/\d+/$")),
    ("GET", re.compile(r"^/blits/$")),
    ("GET", re.compile(r"^/blits/\d+/$")),
)

_server_key = None


def server_private_key() -> ec.EllipticCurvePrivateKey:
    """`SECRET_KEY` dan hosil qilingan doimiy P-256 kaliti."""
    global _server_key
    if _server_key is None:
        seed = hashlib.sha256(b"avtotest-web-tunnel:" + settings.SECRET_KEY.encode()).digest()
        order = int("FFFFFFFF00000000FFFFFFFFFFFFFFFFBCE6FAADA7179E84F3B9CAC2FC632551", 16)
        scalar = int.from_bytes(seed, "big") % (order - 1) + 1
        _server_key = ec.derive_private_key(scalar, ec.SECP256R1())
    return _server_key


def server_public_key_raw() -> bytes:
    return server_private_key().public_key().public_bytes(
        serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
    )


def session_key(client_pub_raw: bytes) -> bytes:
    client_pub = ec.EllipticCurvePublicKey.from_encoded_point(ec.SECP256R1(), client_pub_raw)
    shared = server_private_key().exchange(ec.ECDH(), client_pub)
    return HKDF(
        algorithm=hashes.SHA256(), length=32, salt=client_pub_raw, info=HKDF_INFO
    ).derive(shared)


def seal(key: bytes, payload: dict) -> bytes:
    iv = os.urandom(IV_LEN)
    return iv + AESGCM(key).encrypt(iv, json.dumps(payload, ensure_ascii=False).encode(), None)


def is_allowed(method: str, path: str) -> bool:
    return any(method == m and pattern.match(path) for m, pattern in ALLOWED)


def inner_request(outer, method: str, path: str, query: dict, body, token: str | None):
    """Konvertdagi so'rovdan odatdagi Django so'rovini yasaydi."""
    raw = b"" if body is None else json.dumps(body).encode()
    environ = {
        key: value for key, value in outer.META.items()
        if not key.startswith("HTTP_AUTHORIZATION")
    }
    environ.update({
        "REQUEST_METHOD": method,
        "PATH_INFO": API_PREFIX + path,
        "QUERY_STRING": urlencode({k: v for k, v in (query or {}).items() if v is not None}),
        "CONTENT_TYPE": "application/json",
        "CONTENT_LENGTH": str(len(raw)),
        "wsgi.input": io.BytesIO(raw),
    })
    if token:
        environ["HTTP_AUTHORIZATION"] = f"Bearer {token}"
    return WSGIRequest(environ)


def dispatch(request) -> tuple[int, object]:
    match = resolve(request.path_info)
    request.resolver_match = match
    response = match.func(request, *match.args, **match.kwargs)
    if hasattr(response, "render"):
        response.render()
    if response.status_code == 204 or not response.content:
        return response.status_code, None
    try:
        return response.status_code, json.loads(response.content)
    except ValueError:
        return response.status_code, None


@never_cache
@require_GET
def tunnel_key(request):
    """Serverning ochiq kaliti (sir emas)."""
    return JsonResponse({"k": base64.urlsafe_b64encode(server_public_key_raw()).decode().rstrip("=")})


@csrf_exempt
@never_cache
@require_POST
def tunnel(request):
    started = time.monotonic()
    data = request.body
    if not (PUBLIC_KEY_LEN + IV_LEN < len(data) <= MAX_BODY):
        return HttpResponse(status=400)
    client_pub, iv, sealed = data[:PUBLIC_KEY_LEN], data[PUBLIC_KEY_LEN:PUBLIC_KEY_LEN + IV_LEN], data[PUBLIC_KEY_LEN + IV_LEN:]
    try:
        key = session_key(client_pub)
        envelope = json.loads(AESGCM(key).decrypt(iv, sealed, None))
        method = str(envelope["m"]).upper()
        path = str(envelope["p"])
    except (ValueError, InvalidTag, KeyError, TypeError):
        return HttpResponse(status=400)

    if not is_allowed(method, path):
        status, body = 404, {"detail": "Topilmadi."}
    else:
        inner = inner_request(request, method, path, envelope.get("q"), envelope.get("b"), envelope.get("t"))
        try:
            status, body = dispatch(inner)
        except Resolver404:
            status, body = 404, {"detail": "Topilmadi."}
        except Exception:  # noqa: BLE001 — ichki xato tashqariga oshkor bo'lmasin
            logger.exception("tunnel: %s %s", method, path)
            status, body = 500, {"detail": "Server xatosi."}

    # Server logida ichki yo'l ko'rinadi (Network'da ko'rinmaydi):
    #   tunnel GET /questions/?page=2 -> 200 75ms
    query = urlencode(envelope.get("q") or {})
    logger.info("tunnel %s %s%s -> %s %dms", method, path, f"?{query}" if query else "",
                status, (time.monotonic() - started) * 1000)
    return HttpResponse(seal(key, {"s": status, "b": body}), content_type="application/octet-stream")
