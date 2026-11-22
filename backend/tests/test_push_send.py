"""FCM yuborish: til, 500 lik bo'laklar, yaroqsiz tokenlar, worker."""

import pytest
from django.core.management import call_command
from firebase_admin import exceptions, messaging

from apps.notifications import push
from apps.notifications.models import Notification, PushDevice

pytestmark = pytest.mark.django_db
S = Notification.PushStatus


@pytest.fixture
def sent(monkeypatch):
    """`_send_multicast` o'rniga yozib boruvchi; `sent.fail` = {token: exc}."""
    class Calls(list):
        fail: dict

    calls = Calls()
    fail = {}

    def fake(tokens, title, body, data):
        calls.append({"tokens": list(tokens), "title": title, "body": body, "data": data})
        return [(t not in fail, fail.get(t)) for t in tokens]

    monkeypatch.setattr(push, "is_configured", lambda: True)
    monkeypatch.setattr(push, "_send_multicast", fake)
    calls.fail = fail
    return calls


def user(django_user_model, phone, lang="uz"):
    u = django_user_model.objects.create_user(phone, "pass1234")
    u.language = lang
    u.save(update_fields=["language"])
    return u


def device(u, token, active=True):
    return PushDevice.objects.create(user=u, token=token, platform="android", is_active=active)


def note(recipients=None, **kw):
    kw = {"title_uz": "Salom", "body_uz": "Matn", "push_status": S.PENDING, **kw}
    if recipients is not None:
        kw["audience"] = Notification.Audience.SELECTED
    n = Notification.objects.create(**kw)
    if recipients is not None:
        n.recipients.set(recipients)
    return n


def test_language_per_user(sent, django_user_model):
    uz, kr, ru = (user(django_user_model, f"+99890100000{i}", lang)
                  for i, lang in enumerate(["uz", "kr", "ru"]))
    for u in (uz, kr, ru):
        device(u, f"t-{u.language}")
    n = note([uz, kr, ru], title_cry="Салом", body_cry="Матн", title_ru="")
    assert push.deliver(n) == (3, 0)
    by_token = {c["tokens"][0]: c for c in sent}
    assert by_token["t-uz"]["title"] == "Salom"
    assert by_token["t-kr"]["title"] == "Салом" and by_token["t-kr"]["body"] == "Матн"
    assert by_token["t-ru"]["title"] == "Salom"  # ru bo'sh → uz
    assert by_token["t-uz"]["data"] == {
        "notification_id": str(n.id), "kind": "info", "screen": "notifications"}
    n.refresh_from_db()
    assert (n.push_status, n.push_sent, n.push_failed) == (S.DONE, 3, 0)
    assert n.pushed_at is not None


def test_chunks_of_500(sent, django_user_model):
    u = user(django_user_model, "+998901000001")
    PushDevice.objects.bulk_create(
        [PushDevice(user=u, token=f"t{i}", platform="ios") for i in range(1001)])
    assert push.deliver(note([u])) == (1001, 0)
    assert [len(c["tokens"]) for c in sent] == [500, 500, 1]


def test_invalid_token_deactivated(sent, django_user_model):
    u = user(django_user_model, "+998901000001")
    device(u, "good")
    device(u, "gone")
    device(u, "bad")
    sent.fail["gone"] = messaging.UnregisteredError("unregistered")
    sent.fail["bad"] = exceptions.InvalidArgumentError("invalid token")
    assert push.deliver(note([u])) == (1, 2)
    active = set(PushDevice.objects.filter(is_active=True).values_list("token", flat=True))
    assert active == {"good"}
    assert PushDevice.objects.get(token="gone").last_error


def test_other_error_counts_failed_keeps_device(sent, django_user_model):
    u = user(django_user_model, "+998901000001")
    device(u, "busy")
    sent.fail["busy"] = exceptions.UnavailableError("try later")
    assert push.deliver(note([u])) == (0, 1)
    assert PushDevice.objects.get(token="busy").is_active


def test_all_audience_targets_all_active_devices(sent, django_user_model):
    a = user(django_user_model, "+998901000001")
    b = user(django_user_model, "+998901000002")
    device(a, "a")
    device(b, "b")
    device(b, "old", active=False)
    assert push.deliver(note()) == (2, 0)
    assert sorted(t for c in sent for t in c["tokens"]) == ["a", "b"]


def test_selected_skips_others(sent, django_user_model):
    a = user(django_user_model, "+998901000001")
    b = user(django_user_model, "+998901000002")
    device(a, "a")
    device(b, "b")
    push.deliver(note([a]))
    assert [t for c in sent for t in c["tokens"]] == ["a"]


def test_no_devices_done_zero(sent, django_user_model):
    n = note([user(django_user_model, "+998901000001")])
    assert push.deliver(n) == (0, 0)
    n.refresh_from_db()
    assert n.push_status == S.DONE and sent == []


def test_unconfigured_marks_failed(monkeypatch, django_user_model):
    monkeypatch.setattr(push, "is_configured", lambda: False)
    u = user(django_user_model, "+998901000001")
    device(u, "a")
    n = note([u])
    assert push.deliver(n) == (0, 0)
    n.refresh_from_db()
    assert n.push_status == S.FAILED


def test_claim_marks_sending_once(sent):
    n = note()
    claimed = push.claim_next()
    assert claimed.pk == n.pk
    claimed.refresh_from_db()
    assert claimed.push_status == S.SENDING
    assert push.claim_next() is None


def test_worker_once_processes_pending(sent, django_user_model):
    u = user(django_user_model, "+998901000001")
    device(u, "a")
    n1, n2 = note([u]), note()
    skipped = note([u], push_status=S.NONE)
    call_command("push_worker", "--once")
    statuses = dict(Notification.objects.values_list("pk", "push_status"))
    assert statuses[n1.pk] == S.DONE and statuses[n2.pk] == S.DONE
    assert statuses[skipped.pk] == S.NONE
    assert len(sent) == 2


def test_worker_resets_stuck_sending(sent):
    n = note(push_status=S.SENDING)
    call_command("push_worker", "--once")
    n.refresh_from_db()
    assert n.push_status == S.DONE


def test_multicast_uses_registration_tokens(monkeypatch, settings):
    """`fids` — Firebase Installation ID, qurilma tokeni emas: FCM NotRegistered qaytaradi."""
    captured = {}

    def fake_send(message, app=None):
        captured["message"] = message

        class R:
            responses = [type("X", (), {"success": True, "exception": None})()]
        return R()

    monkeypatch.setattr(messaging, "send_each_for_multicast", fake_send)
    monkeypatch.setattr(push, "_firebase", lambda: None)
    push._send_multicast(["reg-token-1"], "t", "b", {"k": "v"})
    m = captured["message"]
    assert m.tokens == ["reg-token-1"]
    assert not getattr(m, "fids", None)
