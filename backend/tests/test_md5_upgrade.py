"""Ko'chirilgan MD5 parollar bilan kirish ishlaydi va PBKDF2 ga yangilanadi."""

import pytest
from django.contrib.auth.hashers import MD5PasswordHasher
from django.test import override_settings

from apps.accounts.models import User

pytestmark = pytest.mark.django_db

PROD_HASHERS = [
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
    "django.contrib.auth.hashers.MD5PasswordHasher",
]


@override_settings(PASSWORD_HASHERS=PROD_HASHERS)
def test_md5_password_logs_in_and_upgrades(api):
    user = User.objects.create(phone="+998901110022")
    User.objects.filter(pk=user.pk).update(
        password=MD5PasswordHasher().encode("parol123", MD5PasswordHasher().salt())
    )

    response = api.post("/api/v1/auth/login/",
                        {"phone": user.phone, "password": "parol123"}, format="json")
    assert response.status_code == 200

    user.refresh_from_db()
    assert user.password.startswith("pbkdf2_sha256$")
