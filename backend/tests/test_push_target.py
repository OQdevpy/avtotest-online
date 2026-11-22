"""Bildirishnoma bosilganda qayerga kirishi: admin tanlaydi, push va ro'yxat API'da keladi."""

import pytest
from django.core.exceptions import ValidationError

from apps.notifications import push
from apps.notifications.models import Notification, PushDevice

pytestmark = pytest.mark.django_db
T = Notification.Target


@pytest.fixture
def sent(monkeypatch):
    calls = []
    monkeypatch.setattr(push, "is_configured", lambda: True)
    monkeypatch.setattr(push, "_send_multicast",
                        lambda tokens, title, body, data: calls.append(data) or [(True, None)] * len(tokens))
    return calls


def test_default_target_is_notifications_list(sent, student):
    PushDevice.objects.create(user=student, token="t", platform="android")
    n = Notification.objects.create(title_uz="X", push_status="pending")
    push.deliver(n)
    assert sent[0]["screen"] == "notifications" and sent[0]["url"] == ""


def test_target_and_url_in_push_data(sent, student):
    PushDevice.objects.create(user=student, token="t", platform="android")
    n = Notification.objects.create(title_uz="X", push_status="pending",
                                    target=T.URL, url="https://t.me/prava777")
    push.deliver(n)
    assert (sent[0]["screen"], sent[0]["url"]) == ("url", "https://t.me/prava777")


def test_url_target_requires_url():
    with pytest.raises(ValidationError):
        Notification(title_uz="X", target=T.URL, url="").full_clean()


def test_list_api_returns_target(api, auth, student):
    Notification.objects.create(title_uz="X", target=T.BILETLAR)
    auth(api, student)
    data = api.get("/api/v1/notifications/").json()
    row = (data["results"] if isinstance(data, dict) else data)[0]
    assert (row["target"], row["url"]) == ("biletlar", "")


def test_admin_action_sets_target(client, django_user_model, settings, student):
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    client.force_login(django_user_model.objects.create_superuser("+998901119999", "Admin12345"))
    base = {"action": "send_notification", "_selected_action": [student.pk], "apply": "1",
            "kind": "pro", "title_uz": "Chegirma"}
    r = client.post("/admin/accounts/user/", {**base, "target": "url", "url": ""})
    assert r.status_code == 200 and r.context["form"].errors["url"]
    r = client.post("/admin/accounts/user/", {**base, "target": "pro", "url": ""})
    assert r.status_code == 302
    assert Notification.objects.get().target == "pro"
