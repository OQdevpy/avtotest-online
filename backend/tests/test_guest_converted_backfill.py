"""0012: avval mehmondan o'tganlar belgilanadi."""

from datetime import timedelta

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.utils import timezone

pytestmark = pytest.mark.django_db(transaction=True)


def migrate(target):
    ex = MigrationExecutor(connection)
    ex.loader.build_graph()
    ex.migrate([target])
    return ex.loader.project_state([target]).apps


def test_backfill_marks_former_guests():
    old = migrate(("accounts", "0011_user_guest_converted_at"))
    User = old.get_model("accounts", "User")
    Device = old.get_model("accounts", "Device")
    now = timezone.now()
    former = User.objects.create(phone="+998901000001", role="student")
    Device.objects.create(user=former, platform="mobile", refresh_jti="a1", expires_at=now + timedelta(days=3), is_active=False)
    Device.objects.create(user=former, platform="mobile", refresh_jti="a2", expires_at=None)
    direct = User.objects.create(phone="+998901000002", role="student")
    Device.objects.create(user=direct, platform="mobile", refresh_jti="b1", expires_at=None)
    web = User.objects.create(phone="+998901000003", role="student")
    Device.objects.create(user=web, platform="web", refresh_jti="c1", expires_at=now + timedelta(days=12))
    still_guest = User.objects.create(phone="g0000000001", role="guest")
    Device.objects.create(user=still_guest, platform="mobile", refresh_jti="d1", expires_at=now + timedelta(days=3))

    new = migrate(("accounts", "0012_backfill_guest_converted_at"))
    User = new.get_model("accounts", "User")
    marked = set(User.objects.filter(guest_converted_at__isnull=False).values_list("phone", flat=True))
    assert marked == {"+998901000001"}
    migrate(("accounts", "0012_backfill_guest_converted_at"))
