"""Django admin'da talaba qo'shish — telefon xatolari 500 emas, forma xatosi.

Raqam formaning "band" tekshiruvidan oldin normallashadi (Student.clean_fields):
"901234567" bazadagi "+998901234567" bilan to'qnashadi, noto'g'ri raqam esa
maydon xatosi bo'lib chiqadi.
"""

import pytest

from apps.billing.models import Student

pytestmark = pytest.mark.django_db

URL = "/admin/billing/student/add/"


@pytest.fixture
def admin_client(client, django_user_model, settings):
    # Forma xatosida admin sahifasi qayta chiziladi — testda collectstatic
    # manifest'i yo'q, shuning uchun oddiy statik saqlash.
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    user = django_user_model.objects.create_superuser("+998901119999", "Admin12345")
    client.force_login(user)
    return client


def post(client, phone, name="Yangi talaba"):
    return client.post(URL, {"name": name, "phone": phone, "password": "123456",
                             "hujjat": "-", "is_active": "on"})


def test_short_phone_saved_normalized(admin_client):
    response = post(admin_client, "931110002")
    assert response.status_code == 302
    assert Student.objects.get().phone == "+998931110002"


def test_invalid_phone_is_form_error(admin_client):
    response = post(admin_client, "12345")
    assert response.status_code == 200
    assert "+998XXXXXXXXX" in response.content.decode()
    assert not Student.objects.exists()


def test_duplicate_phone_written_differently_is_form_error(admin_client):
    Student.objects.create(name="Bor", phone="+998931110001", password="111111")
    response = post(admin_client, "931110001")
    assert response.status_code == 200
    assert Student.objects.count() == 1
    assert "errorlist" in response.content.decode()
