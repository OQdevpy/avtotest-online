"""Bildirishnoma kimga ko'rinadi: hammaga (all) yoki tanlanganlarga (selected)."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor

from apps.notifications.models import Notification
from apps.notifications.views import visible_to

pytestmark = pytest.mark.django_db

URL = "/api/v1/notifications/"


def make(**kw):
    kw.setdefault("title_uz", "Salom")
    return Notification.objects.create(**kw)


def test_all_visible_to_everyone(student, other_student):
    n = make(audience=Notification.Audience.ALL)
    assert n in visible_to(student)
    assert n in visible_to(other_student)


def test_selected_visible_only_to_recipients(student, other_student):
    n = make(audience=Notification.Audience.SELECTED)
    n.recipients.set([student])
    assert n in visible_to(student)
    assert n not in visible_to(other_student)


def test_inactive_hidden(student):
    make(audience=Notification.Audience.ALL, is_active=False)
    assert not visible_to(student).exists()


def test_list_endpoint_no_duplicates(api, auth, student, other_student):
    n = make(audience=Notification.Audience.SELECTED)
    n.recipients.set([student, other_student])
    auth(api, student)
    data = api.get(URL).json()
    rows = data["results"] if isinstance(data, dict) else data
    assert [r["id"] for r in rows] == [n.id]
    assert api.get(URL + "unread-count/").json() == {"unread": 1}


@pytest.mark.django_db(transaction=True)
def test_migration_moves_user_to_recipients(django_user_model):
    def migrate(target):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(target)
        return executor.loader.project_state(target).apps

    before = [("notifications", "0001_initial")]
    after = [("notifications", "0002_audience_recipients")]
    old = migrate(before)
    OldN = old.get_model("notifications", "Notification")
    # accounts jadvali oxirgi holatda qoladi — haqiqiy model bilan yaratamiz
    u = django_user_model.objects.create_user("+998901112233", "pass1234")
    targeted = OldN.objects.create(title_uz="T", user_id=u.pk)
    broadcast = OldN.objects.create(title_uz="B")

    new = migrate(after)
    NewN = new.get_model("notifications", "Notification")
    t = NewN.objects.get(pk=targeted.pk)
    b = NewN.objects.get(pk=broadcast.pk)
    assert t.audience == "selected"
    assert list(t.recipients.values_list("pk", flat=True)) == [u.pk]
    assert b.audience == "all"
    assert b.recipients.count() == 0
    migrate(MigrationExecutor(connection).loader.graph.leaf_nodes())  # oxirgi holatga qaytarish
