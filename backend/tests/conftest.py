import pytest
from rest_framework.test import APIClient
from rest_framework_simplejwt.tokens import RefreshToken

PASSWORD = "pass1234"


@pytest.fixture
def api():
    return APIClient()


@pytest.fixture
def auth():
    """`auth(client, user)` — mijozga shu foydalanuvchining JWT'sini biriktiradi."""

    def _auth(client, user):
        access = RefreshToken.for_user(user).access_token
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
        return client

    return _auth


@pytest.fixture
def student(django_user_model):
    return django_user_model.objects.create_user(
        "+998901110001", PASSWORD, full_name="O'quvchi"
    )


@pytest.fixture
def other_student(django_user_model):
    return django_user_model.objects.create_user(
        "+998901110002", PASSWORD, full_name="Boshqa o'quvchi"
    )


@pytest.fixture
def teacher(django_user_model):
    # Task 2 da `role="teacher"` ga o'tkaziladi.
    return django_user_model.objects.create_user(
        "+998901110003", PASSWORD, full_name="O'qituvchi", is_staff=True
    )


@pytest.fixture
def admin_user(django_user_model):
    # Task 2 da `role="admin"` ga o'tkaziladi.
    return django_user_model.objects.create_superuser(
        "+998901110004", PASSWORD, full_name="Shef"
    )
