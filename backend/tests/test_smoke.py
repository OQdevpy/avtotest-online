import pytest

pytestmark = pytest.mark.django_db


def test_sections_requires_auth(api):
    assert api.get("/api/v1/sections/").status_code == 401


def test_sections_returns_list_for_authenticated_user(api, student, auth):
    auth(api, student)
    assert api.get("/api/v1/sections/").status_code == 200
