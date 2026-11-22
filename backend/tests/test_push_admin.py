"""Admin: tanlangan foydalanuvchilarga bildirishnoma (push) yuborish."""

import pytest
from django.contrib import admin
from django.contrib.auth.models import Group
from django.core.management import call_command
from django.test import RequestFactory

from apps.accounts.models import User
from apps.notifications.models import Notification, PushDevice

pytestmark = pytest.mark.django_db

USERS = "/admin/accounts/user/"
NOTES = "/admin/notifications/notification/"
S = Notification.PushStatus


@pytest.fixture
def admin_client(client, django_user_model, settings):
    settings.STORAGES = {
        **settings.STORAGES,
        "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"},
    }
    user = django_user_model.objects.create_superuser("+998901119999", "Admin12345")
    client.force_login(user)
    return client


@pytest.fixture
def people(django_user_model):
    a = django_user_model.objects.create_user("+998901000001", "pass1234")
    b = django_user_model.objects.create_user("+998901000002", "pass1234")
    c = django_user_model.objects.create_user("+998901000003", "pass1234")
    PushDevice.objects.create(user=a, token="a", platform="android")
    return a, b, c


def post_action(client, ids, **extra):
    data = {"action": "send_notification", "_selected_action": [u.pk for u in ids], **extra}
    return client.post(USERS, data)


def test_action_shows_confirmation(admin_client, people):
    a, b, _ = people
    r = post_action(admin_client, [a, b])
    assert r.status_code == 200
    text = r.content.decode()
    assert "Bildirishnoma yuborish" in text
    assert r.context["selected_count"] == 2
    assert r.context["with_device"] == 1
    assert Notification.objects.count() == 0


def test_action_creates_pending_for_selected(admin_client, people):
    a, b, c = people
    r = post_action(admin_client, [a, b], apply="1", kind="pro",
                    title_uz="Chegirma", title_ru="Скидка", title_cry="", body_uz="50%")
    assert r.status_code == 302
    n = Notification.objects.get()
    assert (n.audience, n.push_status, n.kind) == (
        Notification.Audience.SELECTED, S.PENDING, "pro")
    assert (n.title_uz, n.title_ru, n.body_uz) == ("Chegirma", "Скидка", "50%")
    assert set(n.recipients.all()) == {a, b}


def test_action_requires_title_uz(admin_client, people):
    r = post_action(admin_client, [people[0]], apply="1", kind="info", title_uz="")
    assert r.status_code == 200
    assert r.context["form"].errors["title_uz"]
    assert Notification.objects.count() == 0


def test_notification_admin_add_all_with_push_pending(admin_client):
    r = admin_client.post(NOTES + "add/", {
        "kind": "info", "is_active": "on", "audience": "all", "send_push": "on",
        "title_uz": "Yangilik", "title_ru": "", "title_cry": "",
        "body_uz": "", "body_ru": "", "body_cry": ""})
    assert r.status_code == 302, r.context["adminform"].form.errors
    n = Notification.objects.get()
    assert n.push_status == S.PENDING and n.audience == "all"


def test_notification_admin_add_without_push(admin_client):
    admin_client.post(NOTES + "add/", {
        "kind": "info", "is_active": "on", "audience": "all",
        "title_uz": "Jim", "title_ru": "", "title_cry": "",
        "body_uz": "", "body_ru": "", "body_cry": ""})
    assert Notification.objects.get().push_status == S.NONE


def test_resend_sets_pending(admin_client):
    n = Notification.objects.create(title_uz="X", push_status=S.DONE, push_sent=5)
    admin_client.post(NOTES, {"action": "resend_push", "_selected_action": [n.pk]})
    n.refresh_from_db()
    assert n.push_status == S.PENDING


def test_has_device_filter(admin_client, people):
    r = admin_client.get(USERS, {"push": "yes"})
    phones = [u.phone for u in r.context["cl"].result_list]
    assert phones == ["+998901000001"]  # admin'ning o'zida qurilma yo'q
    r = admin_client.get(USERS, {"push": "no"})
    assert "+998901000001" not in [u.phone for u in r.context["cl"].result_list]


def test_teacher_has_no_send_action(django_user_model):
    call_command("setup_groups")
    t = django_user_model.objects.create_user("+998901000009", "pass1234", is_staff=True)
    t.groups.add(Group.objects.get(name="teacher"))
    request = RequestFactory().get(USERS)
    request.user = t
    assert "send_notification" not in admin.site._registry[User].get_actions(request)


def test_select_across_uses_filters(admin_client, people, django_user_model):
    a, b, c = people
    PushDevice.objects.create(user=b, token="b", platform="ios")
    r = admin_client.post(USERS + "?push=yes", {
        "action": "send_notification", "_selected_action": [a.pk], "select_across": "1"})
    assert r.context["selected_count"] == 2 and r.context["select_across"]
    admin_client.post(USERS + "?push=yes", {
        "action": "send_notification", "_selected_action": [a.pk], "select_across": "1",
        "apply": "1", "kind": "info", "title_uz": "Hammaga filtrdan"})
    assert set(Notification.objects.get().recipients.all()) == {a, b}
