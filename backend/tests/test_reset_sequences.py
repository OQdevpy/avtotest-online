"""`reset_sequences` — backup/import'dan keyin eskirgan id hisoblagichlarini tiklaydi.

Postgres'da tekshiriladi (sqlite'da sequence yo'q — buyruq jim o'tadi).
"""

from io import StringIO

import pytest
from django.core.management import call_command
from django.db import connection

from apps.content.models import Section

postgres_only = pytest.mark.skipif(connection.vendor != "postgresql",
                                   reason="sequence faqat Postgres'da")


def test_command_is_noop_without_postgres(db):
    out = StringIO()
    call_command("reset_sequences", stdout=out)
    if connection.vendor != "postgresql":
        assert "o'tkazib" in out.getvalue()


@postgres_only
def test_stale_sequence_is_moved_past_max_id(db):
    Section.objects.create(id=50, name_uz="Import qilingan", order=1)
    with connection.cursor() as cursor:
        cursor.execute("SELECT setval(pg_get_serial_sequence('content_section', 'id'), 1)")

    call_command("reset_sequences", stdout=StringIO())

    assert Section.objects.create(name_uz="Yangi", order=2).id == 51


@postgres_only
def test_sequence_never_moves_backwards(db):
    with connection.cursor() as cursor:
        cursor.execute("SELECT setval(pg_get_serial_sequence('content_section', 'id'), 500)")
    call_command("reset_sequences", stdout=StringIO())
    assert Section.objects.create(name_uz="Yangi", order=1).id == 501


@postgres_only
def test_foreign_table_does_not_break_command(db):
    """Backup'dagi begona jadval (matn ustuni sequence'ga bog'langan) buyruqni yiqitmasin."""
    with connection.cursor() as cursor:
        cursor.execute("CREATE SEQUENCE legacy_seq")
        cursor.execute("CREATE TABLE legacy_codes (code text DEFAULT nextval('legacy_seq'))")
        cursor.execute("ALTER SEQUENCE legacy_seq OWNED BY legacy_codes.code")
        cursor.execute("INSERT INTO legacy_codes (code) VALUES ('abc')")
    Section.objects.create(id=70, name_uz="Import", order=1)
    with connection.cursor() as cursor:
        cursor.execute("SELECT setval(pg_get_serial_sequence('content_section', 'id'), 1)")

    call_command("reset_sequences", stdout=StringIO())  # xato ko'tarmaydi

    assert Section.objects.create(name_uz="Yangi", order=2).id == 71
