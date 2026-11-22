"""Bosh sahifa karuseli: admin rasm yuklaydi, ilova o'z tilidagi rasmni oladi."""

import io
from datetime import timedelta

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from PIL import Image

from apps.promo.models import Slide

pytestmark = pytest.mark.django_db
URL = "/api/v1/slides/"


def png(name="s.png", size=(1200, 500)):
    buf = io.BytesIO()
    Image.new("RGB", size, (237, 2, 10)).save(buf, "PNG")
    return SimpleUploadedFile(name, buf.getvalue(), content_type="image/png")


@pytest.fixture(autouse=True)
def media(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path


def slide(**kw):
    kw.setdefault("title", "Slayd")
    kw.setdefault("image_uz", png("uz.png"))
    return Slide.objects.create(**kw)


def get(api, **params):
    r = api.get(URL, params)
    assert r.status_code == 200, r.data
    return r.json()


def test_active_slides_in_order(api, auth, student):
    b = slide(title="B", order=2)
    a = slide(title="A", order=1)
    slide(title="off", is_active=False)
    auth(api, student)
    assert [s["id"] for s in get(api)] == [a.id, b.id]


def test_shape_and_absolute_url(api, auth, student):
    s = slide(action=Slide.Action.URL, url="https://prava777.uz/kurs")
    auth(api, student)
    row = get(api)[0]
    assert set(row) == {"id", "image_url", "action", "url"}
    assert row["image_url"].startswith("http://testserver/media/slides/")
    assert (row["action"], row["url"]) == ("url", "https://prava777.uz/kurs")
    assert s.id == row["id"]


def test_language_image_with_fallback(api, auth, student):
    slide(image_ru=png("ru.png"))
    auth(api, student)
    assert "ru" in get(api, lang="ru")[0]["image_url"].rsplit("/", 1)[-1]
    assert "uz" in get(api, lang="kr")[0]["image_url"].rsplit("/", 1)[-1]  # kirill yo'q → uz


def test_date_window(api, auth, student):
    now = timezone.now()
    live = slide(title="live", starts_at=now - timedelta(days=1), ends_at=now + timedelta(days=1))
    slide(title="future", starts_at=now + timedelta(days=1))
    slide(title="past", ends_at=now - timedelta(minutes=1))
    auth(api, student)
    assert [s["id"] for s in get(api)] == [live.id]


def test_audience(api, auth, student, django_user_model):
    every = slide(title="all")
    guests = slide(title="g", audience=Slide.Audience.GUEST)
    free = slide(title="f", audience=Slide.Audience.FREE)
    pro = slide(title="p", audience=Slide.Audience.PRO)

    auth(api, student)  # PRO'siz o'quvchi
    assert {s["id"] for s in get(api)} == {every.id, free.id}

    student.is_pro, student.pro_until = True, timezone.now() + timedelta(days=5)
    student.save()
    assert {s["id"] for s in get(api)} == {every.id, pro.id}

    r = api.post("/api/v1/auth/guest/", {"device_id": "d" * 32, "lang": "uz"}, format="json")
    api.credentials(HTTP_AUTHORIZATION=f"Bearer {r.data['tokens']['access']}")
    assert {s["id"] for s in get(api)} == {every.id, guests.id, free.id}


def test_url_action_requires_url():
    from django.core.exceptions import ValidationError

    s = Slide(title="x", image_uz=png(), action=Slide.Action.URL, url="")
    with pytest.raises(ValidationError):
        s.full_clean()


def test_admin_upload(client, django_user_model, settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    client.force_login(django_user_model.objects.create_superuser("+998901119999", "Admin12345"))
    r = client.post("/admin/promo/slide/add/", {
        "title": "Chegirma", "image_uz": png(), "action": "pro", "url": "",
        "audience": "all", "order": 1, "is_active": "on"})
    assert r.status_code == 302, r.context["adminform"].form.errors
    s = Slide.objects.get()
    assert s.image_uz.name.startswith("slides/") and s.action == "pro"
    assert client.get("/admin/promo/slide/").status_code == 200


def test_requires_session(api):
    assert api.get(URL).status_code == 401
