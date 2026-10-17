"""Postgres id hisoblagichlarini (sequence) jadvaldagi eng katta id'gacha suradi.

Backup tiklanganda yoki import eski id'lar bilan yozganda hisoblagich ortda
qoladi va keyingi INSERT band id'ni oladi (`duplicate key ... _pkey`). Buyruq
barcha jadvallarni, `django_migrations` ni ham, tuzatadi. Hisoblagich faqat
oldinga suriladi — takror ishga tushirish xavfsiz, shuning uchun konteyner
har ko'tarilganda `migrate` dan oldin chaqiriladi.

    python manage.py reset_sequences
"""

from django.core.management.base import BaseCommand
from django.db import connection

SQL = """
DO $$
DECLARE
    r record;
    max_id bigint;
BEGIN
    FOR r IN
        SELECT c.table_name, c.column_name,
               pg_get_serial_sequence(quote_ident(c.table_name), c.column_name) AS seq
        FROM information_schema.columns c
        JOIN information_schema.tables t
          ON t.table_schema = c.table_schema AND t.table_name = c.table_name
        WHERE c.table_schema = current_schema() AND t.table_type = 'BASE TABLE'
          -- Faqat son turidagi id: backup'dagi begona jadvallar (matn ustuni va h.k.) o'tkazib yuboriladi
          AND c.data_type IN ('smallint', 'integer', 'bigint')
    LOOP
        CONTINUE WHEN r.seq IS NULL;
        -- Bitta jadvaldagi xato (huquq, begona sxema) qolganlarini to'xtatmasin
        BEGIN
            EXECUTE format('SELECT MAX(%I) FROM %I', r.column_name, r.table_name) INTO max_id;
            CONTINUE WHEN max_id IS NULL;
            -- Faqat oldinga: hisoblagich max_id dan ortda bo'lsagina suriladi.
            EXECUTE format(
                'SELECT setval(%L, %s) WHERE (SELECT CASE WHEN is_called THEN last_value ELSE last_value - 1 END FROM %s) < %s',
                r.seq, max_id, r.seq, max_id
            );
        EXCEPTION WHEN OTHERS THEN
            RAISE WARNING 'reset_sequences: % o''tkazib yuborildi (%)', r.table_name, SQLERRM;
        END;
    END LOOP;
END $$;
"""


class Command(BaseCommand):
    help = "Postgres id hisoblagichlarini jadvaldagi eng katta id'gacha suradi"

    def handle(self, *args, **options):
        if connection.vendor != "postgresql":
            self.stdout.write("Postgres emas — o'tkazib yuborildi.")
            return
        with connection.cursor() as cursor:
            cursor.execute(SQL)
        self.stdout.write(self.style.SUCCESS("id hisoblagichlari tekshirildi va tuzatildi."))
