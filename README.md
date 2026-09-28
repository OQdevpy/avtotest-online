# AvtoTest Online — yagona backend

AvtoTest loyihasining markazlashgan backendi. Ilgari kontent va foydalanuvchilar
to'rt joyda ayri yashardi (sayt, mobil ilova, admin-panel JSON fayllari, desktop
`db.enc`); endi hammasi bitta Django loyihasi va bitta baza.

**Stack:** Python 3.12+, Django 6, DRF, PostgreSQL, JWT (SimpleJWT), drf-spectacular.

**Hujjatlar:** `/api/docs/` (Swagger) · `/api/redoc/` · `/api/schema/` (OpenAPI JSON)

- Dizayn: [docs/superpowers/specs/2026-09-27-unified-backend-design.md](docs/superpowers/specs/2026-09-27-unified-backend-design.md)
- Reja: [docs/superpowers/plans/2026-09-27-unified-backend.md](docs/superpowers/plans/2026-09-27-unified-backend.md)

---

## Ishga tushirish

```bash
cd backend
cp .env.example .env          # SECRET_KEY va DB_PASSWORD ni to'ldiring
docker compose up -d --build  # http://localhost:9005
```

Compose ko'tarilganda `migrate` va `collectstatic` avtomatik bajariladi.

Docker'siz:

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py migrate
python manage.py createsuperuser --phone +998901112233
python manage.py setup_groups
python manage.py runserver
```

> `DATABASE_URL` **majburiy** — o'zgaruvchi bo'lmasa ilova ishga tushmaydi.
> `DEBUG=False` bo'lganda `SECRET_KEY` va `ALLOWED_HOSTS` ham majburiy.

### Testlar

```bash
cd backend && .venv/bin/python -m pytest
```

Testlar sqlite'da ishlaydi (`config/settings_test.py`); produksiya Postgres'da.

---

## Ma'lumot ko'chirish

Tartib muhim.

**1. Mavjud mobil bazani tiklash.** `backups/avtotest_mobile_*.sql` yangi bazaga
tiklanadi — foydalanuvchilar, progress va kontent shu yerdan keladi. So'ng
`python manage.py migrate` yangi jadvallarni qo'shadi.

**2. Kontentni admin-panel JSON'laridan yangilash.**

```bash
python manage.py import_content --path ../../admin-panel/src/db --dry-run
python manage.py import_content --path ../../admin-panel/src/db
```

Moslashtirish id bo'yicha (legacy PK'lar saqlangan). Bazada bor-u JSON'da yo'q
yozuv **o'chirilmaydi**. Idempotent.

**3. Eski web bazasidan o'quvchi va to'lovlar.**

```bash
python manage.py import_web --database-url postgresql://... --dry-run
python manage.py import_web --database-url postgresql://...
```

Telefon `+998XXXXXXXXX` ga keltiriladi, ochiq matndagi parol hash qilinadi.
Telefon bo'yicha mavjud foydalanuvchi topilsa **uning paroli, ismi va progressi
tegilmaydi** — faqat bo'sh `branch` va `hujjat` to'ldiriladi.

**4. Rasmlarni WebP'ga o'girish.**

```bash
python manage.py convert_images_to_webp --dry-run
python manage.py convert_images_to_webp
```

---

## Rollar

| Rol | Nima qila oladi |
|---|---|
| `student` | Kontentni o'qiydi, test va imtihon ishlaydi, o'z progressini ko'radi |
| `teacher` | Qo'shimcha: o'z filialidagi o'quvchilar natijasini ko'radi; to'g'ri javob va nashr etilmagan savol ham ko'rinadi |
| `admin` (shef) | Kontent, foydalanuvchi, filial va to'lovni boshqaradi (`manage/`) |

`role` biznes huquqini belgilaydi; Django'ning `is_staff` faqat admin paneliga
kirishni. `setup_groups` admin paneli ichidagi huquqlarni sozlaydi.

---

## Autentifikatsiya

Yadro — JWT (access 1 kun, refresh 90 kun, rotatsiya yoqilgan). Kirish yo'llari:

| Yo'l | Kim ishlatadi |
|---|---|
| `auth/login/` — telefon + parol | Mobil, web |
| `auth/login-code/` — shef bergan kod | Desktop darslik va imtihon |
| `auth/social/` — Apple / Google / Telegram | Mobil |

Har bir kirish `Device` yozuvini yaratadi. Limit platforma bo'yicha (mobil 2,
web va desktop 1), `User.max_devices` bilan qayta yozish mumkin. Muddat ham
platforma bo'yicha: mobilda yo'q, web va desktopda 12 kun — muddati o'tgan
qurilma bilan token yangilanmaydi.

`auth/social/` provayder tokenini **tekshiradi** (Apple imzosi, Google
`tokeninfo`, Telegram `hash`). Provayder sozlanmagan bo'lsa u orqali kirish
ochilmaydi.

---

## Endpointlar

Barcha `GET` so'rovlar `?lang=` ni qo'llaydi (`uz` / `kr` / `qq` / `ru`), so'ng
`Accept-Language`, so'ng `uz`. Bo'sh matn `uz → ru → cry` tartibida zaxiraga tushadi.

### Kontent

`sections/` · `lessons/` · `questions/?lesson=&section=&search=` · `topics/` ·
`tickets/` · `tickets/stats/` · `tickets/{number}/` · `blits/` · `blits/{id}/`

To'g'ri javob (`is_true`) test rejimida qaytmaydi; `?mode=study` bilan ochiladi;
`teacher` va `admin` uchun har doim ochiq. `is_published=False` savol o'quvchiga
hech bir yo'l orqali ko'rinmaydi.

### Imtihon

| Metod | Yo'l |
|---|---|
| POST | `exams/start/` — `{mode: 20\|50}` |
| POST | `exams/{id}/answer/` — `{question, answer}` |
| POST | `exams/{id}/finish/` — serverda baholaydi |
| GET | `exams/` · `exams/{id}/` |

Vaqt tugagach `answer/` `409` qaytaradi; `finish/` esa ishlaydi. `finish/`
ikkinchi marta chaqirilsa `409` — ikkinchi natija yozuvi paydo bo'lmaydi.

### Progress

`progress/lesson-results/` · `ticket-results/` · `blits-results/` ·
`exam-attempts/` · `mistakes/` · `mistakes/{id}/resolve/` · `stats/` ·
`reset/` · `saved/`

Ball **har doim serverda** hisoblanadi — mijoz yuborgan `score` e'tiborga olinmaydi.

### Shef — `manage/` (`admin` roli)

`users/` · `access-codes/` · `sections/` · `lessons/` · `questions/` ·
`answers/` · `topics/` · `tickets/` · `blits/` · `branches/` · `payments/` ·
`payment-reports/`

`POST .../reorder/` — `{"ids": [3, 1, 2]}`, drag-and-drop tartibi.
`POST manage/questions/{id}/image/` va `.../audio/` — multipart yuklash.

`manage/` javoblarida til yig'ilmaydi: uch ustun (`*_uz`, `*_ru`, `*_cry`) ham
ochiq keladi, chunki shef uchalasini tahrirlaydi.

### O'qituvchi — `teacher/`

`students/` · `students/{id}/stats/` · `stats/`

O'qituvchi faqat o'z filialini ko'radi (filiali biriktirilmagan bo'lsa hech
kimni). Begona filial o'quvchisi uchun `404`.

---

## Eski frontlar uchun

`?compat=1` javobga eski nomlarni qo'shadi: `question_uz/ru/cry`,
`answer_uz/ru/cry`, `tartib`. Mobil javoblari semirmasligi uchun default
o'chirilgan.

Quyidagi yo'llar do'kondagi mobil ilova uchun ishlashda davom etadi, lekin
Swagger'da `deprecated` deb belgilangan:

- `GET exam/generate/?count=` → `POST exams/start/`
- `POST progress/exam-attempts/` → `POST exams/{id}/finish/`
