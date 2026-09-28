import pytest

pytestmark = pytest.mark.django_db


def test_sections_requires_auth(api):
    assert api.get("/api/v1/sections/").status_code == 401


def test_sections_returns_list_for_authenticated_user(api, student, auth):
    auth(api, student)
    assert api.get("/api/v1/sections/").status_code == 200


def test_webp_media_content_type(client, settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path
    (tmp_path / "x.webp").write_bytes(b"RIFF0000WEBP")
    response = client.get("/media/x.webp")
    assert response.status_code == 200
    assert response["Content-Type"] == "image/webp"
