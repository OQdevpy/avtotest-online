"""Web ilovalarning shifrlangan kanali — `POST /api/v1/s/` (common/tunnel.py).

Mijoz bu yerda brauzerdagi web ilova bilan bir xil ishni qiladi: ECDH kalit
juftligi, HKDF, AES-GCM.
"""

import base64
import json
import os

import pytest
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.kdf.hkdf import HKDF

from apps.accounts.models import AccessCode

pytestmark = pytest.mark.django_db

URL = "/api/v1/s/"


class WebClient:
    def __init__(self, api):
        self.api = api
        raw = api.get("/api/v1/s/key/").json()["k"]
        server_pub = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
        )
        private = ec.generate_private_key(ec.SECP256R1())
        self.pub = private.public_key().public_bytes(
            serialization.Encoding.X962, serialization.PublicFormat.UncompressedPoint
        )
        shared = private.exchange(ec.ECDH(), server_pub)
        self.key = HKDF(hashes.SHA256(), 32, salt=self.pub, info=b"avtotest-web-v1").derive(shared)
        self.token = None

    def raw(self, envelope):
        iv = os.urandom(12)
        body = self.pub + iv + AESGCM(self.key).encrypt(iv, json.dumps(envelope).encode(), None)
        return self.api.generic("POST", URL, body, content_type="application/octet-stream")

    def call(self, method, path, query=None, body=None):
        response = self.raw({"m": method, "p": path, "q": query or {}, "b": body, "t": self.token})
        assert response.status_code == 200
        assert response["Content-Type"] == "application/octet-stream"
        data = response.content
        inner = json.loads(AESGCM(self.key).decrypt(data[:12], data[12:], None))
        return inner["s"], inner["b"], data

    def login(self, code, device="a" * 64):
        status, body, _ = self.call("POST", "/auth/login-code/", body={
            "code": code, "platform": "web", "device_label": "test", "device_id": device,
        })
        assert status == 200, body
        self.token = body["tokens"]["access"]
        return body


@pytest.fixture
def code(student):
    return AccessCode.generate(user=student).code


def test_public_key_is_p256_point(api):
    raw = api.get("/api/v1/s/key/").json()["k"]
    point = base64.urlsafe_b64decode(raw + "=" * (-len(raw) % 4))
    assert len(point) == 65 and point[0] == 4


def test_login_and_content_through_tunnel(api, code, ticket, question):
    client = WebClient(api)
    login = client.login(code)
    assert login["user"]["role"] == "student"

    status, body, _ = client.call("GET", "/content/version/")
    assert status == 200 and body["version"]

    status, body, _ = client.call("GET", "/questions/", {"mode": "study", "page_size": 200})
    assert status == 200
    answers = body["results"][0]["answers"]
    assert any(a["is_true"] for a in answers)  # query parametrlari uzatildi

    status, body, _ = client.call("GET", "/tickets/1/", {"mode": "study"})
    assert status == 200 and body["questions"][0]["id"] == question.id


def test_nothing_readable_on_the_wire(api, code, question):
    client = WebClient(api)
    client.login(code)
    _, _, wire = client.call("GET", "/questions/", {"mode": "study"})
    # Qisqa belgilar ({, ") tasodifiy shifrlangan baytlarda ham uchraydi —
    # faqat ochiq JSON'da albatta bo'ladigan uzun bo'laklar tekshiriladi.
    for plain in (b"is_true", b"questions", b'"results"', question.text_uz.encode()):
        assert plain not in wire


def test_inner_errors_stay_inside(api, code):
    client = WebClient(api)
    status, body, _ = client.call("GET", "/content/version/")  # tokensiz
    assert status == 401
    status, body, _ = client.call("POST", "/auth/login-code/", body={
        "code": "XXXXXXXX", "platform": "web", "device_id": "d"})
    assert status in (400, 401, 403)


@pytest.mark.parametrize("method,path", [
    ("POST", "/auth/login/"),          # telefon+parol — web kanali orqali yopiq
    ("GET", "/manage/users/"),
    ("GET", "/teacher/students/"),
    ("DELETE", "/auth/devices/1/"),
    ("GET", "/questions/../manage/users/"),
])
def test_only_allowlisted_paths(api, code, admin_user, auth, method, path):
    client = WebClient(api)
    client.login(code)
    status, body, _ = client.call(method, path)
    assert status == 404


def test_tampered_or_garbage_body_rejected(api):
    client = WebClient(api)
    iv = os.urandom(12)
    sealed = bytearray(AESGCM(client.key).encrypt(iv, b'{"m":"GET","p":"/sections/"}', None))
    sealed[-1] ^= 1
    assert api.generic("POST", URL, client.pub + iv + bytes(sealed),
                       content_type="application/octet-stream").status_code == 400
    assert api.generic("POST", URL, b"x" * 100,
                       content_type="application/octet-stream").status_code == 400
    assert api.get(URL).status_code == 405


def test_other_client_key_cannot_read_response(api, code):
    alice, eve = WebClient(api), WebClient(api)
    alice.login(code)
    _, _, wire = alice.call("GET", "/content/version/")
    with pytest.raises(Exception):
        AESGCM(eve.key).decrypt(wire[:12], wire[12:], None)
