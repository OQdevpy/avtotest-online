# Yagona backend — dizayn hujjati

**Sana:** 2026-09-27
**Loyiha:** `avtotest-online/backend`
**Holati:** tasdiqlashga tayyor

---

## 1. Maqsad

Bugun AvtoTest kontenti va foydalanuvchilari to'rt joyda ayri yashaydi: `web/backend`
(sayt, filial, to'lov), `avtotest-mobile-back` (mobil ilova), `avtotest-online/backend`
(yangi, deyarli bo'sh) va `admin-panel` (shef JSON fayllarni tahrirlaydi). Bir savolni
o'zgartirish uchun bir necha joyga qo'l urish kerak, o'quvchining progressi esa qaysi
ilovadan kirganiga qarab turlicha.

Shu hujjat **`avtotest-online/backend`** ni yagona markaziy backendga aylantirish
rejasini belgilaydi: bitta ma'lumotlar bazasi, bitta autentifikatsiya, bitta kontent
manbai, bitta API.

## 2. Qamrov

**Kiradi:** auth va rollar, kontent (savol/javob/bilet/blits/mavzu), imtihon va
baholash, progress va statistika, shef uchun kontent yozish API'si, o'qituvchi uchun
natijalar API'si, filial va to'lov, Django admin, migratsiya buyruqlari, Swagger.

**Kirmaydi (keyingi bosqich):** frontendlarni ulash. Desktop ilovalarga
(`darslik`, `imtihon`, `darslik teacher`, `avtotest-desktop-seoul`) bu bosqichda
**tegilmaydi** — ular hozircha `db.enc` bilan offline ishlayveradi. Backend shunday
quriladiki, ular keyinchalik ulana olsin.

## 3. Qabul qilingan qarorlar

| # | Qaror | Sabab |
|---|---|---|
| 1 | Asos — `avtotest-mobile-back` kodi, `avtotest-online/backend` ga ko'chiriladi | Eng yetuk: Django 6, DRF, JWT, progress, Swagger, ko'p tillilik allaqachon ishlab turibdi |
| 2 | `web/backend` dagi biznes qismi to'liq ko'chadi | Yagona baza. Eski `web/backend` o'rnini bosadi |
| 3 | JWT yadro + bir nechta kirish yo'li | Har bir mijoz o'z odatiy kirish oynasini yo'qotmaydi |
| 4 | O'qituvchi faqat o'quvchilar natijasini ko'radi | Kontent nazorati shefda qoladi |
| 5 | Bitta toza API + eski nom taxalluslari | Mobil o'zgarmaydi, eski frontlarni ulash arzonlashadi |
| 6 | Baza: mobil backup asos, kontent JSON'dan yangilanadi | Foydalanuvchi progressi ham, shefning oxirgi tahriri ham saqlanadi |

## 4. Arxitektura

Bitta Django loyihasi, modulli applar. Har bir app bitta sohaga javob beradi va
boshqalarga faqat model va servis funksiyalari orqali ko'rinadi.

```
backend/
  config/          settings, urls, api_urls
  common/          lang.py, models.py, pagination.py, permissions.py
  apps/
    accounts/      User, rol, Device, AccessCode, SocialAccount
    content/       Section, Lesson, Question, Answer, Ticket, Topic, Blits (+ manage API)
    exams/         ExamSession — imtihon sessiyasi va baholash
    progress/      natijalar, urinishlar, xatolar, saqlanganlar
    billing/       Branch, StudentPayment, PaymentReport
    notifications/ Notification, NotificationRead
    telegramauth/  TelegramAccount
```

`common/lang.py` mobile-back'dan o'zgarishsiz ko'chadi — `resolve_lang`,
`TranslatedField`, `LangSerializerContextMixin`.

## 5. Ma'lumotlar modeli

### 5.1 accounts

**`User`** (`AUTH_USER_MODEL`) — mobile-back'dagi model, quyidagilar qo'shiladi:

| Maydon | Tur | Izoh |
|---|---|---|
| `role` | `student` \| `teacher` \| `admin` | Yangi. Default `student` |
| `branch` | FK → `billing.Branch`, null | Web'dagi `Student.branch` |
| `hujjat` | `+` \| `-`, default `-` | Web'dagi maydon |
| `max_devices` | int, null | Null bo'lsa `settings.MAX_DEVICES_PER_PLATFORM` amal qiladi |

Mavjud maydonlar o'zgarishsiz: `phone` (unique, `+998XXXXXXXXX`), `full_name`,
`language` (`uz`/`kr`/`qq`/`ru`), `dark_theme`, `is_pro`, `pro_until`, `is_active`,
`is_staff`, `is_superuser`, `date_joined`.

`is_staff` faqat Django admin paneliga kirishni belgilaydi. Biznes huquqlari
`role` orqali hal qilinadi.

**`Device`** (yangi) — kim qayerdan kirgan.

| Maydon | Izoh |
|---|---|
| `user` | FK |
| `platform` | `mobile` \| `web` \| `desktop` |
| `refresh_jti` | JWT refresh tokenining `jti` si (unique) |
| `label` | Qurilma nomi, mijoz yuboradi (ixtiyoriy) |
| `created_at`, `last_seen` | |
| `expires_at` | null yoki `created_at + SESSION_DAYS[platform]` |
| `is_active` | |

Kirishda: shu platformadagi faol qurilmalar soni limitdan oshsa,
`403` va `{"detail": "Ushbu hisob allaqachon boshqa qurilmada ochiq."}` qaytadi.
Limit `settings.MAX_DEVICES_PER_PLATFORM = {"mobile": 2, "web": 1, "desktop": 1}`,
`User.max_devices` to'ldirilgan bo'lsa u barcha platformalar uchun ustun turadi.

Muddat platformaga qarab:
`settings.SESSION_DAYS = {"mobile": None, "web": 12, "desktop": 12}`.
`None` — muddat yo'q, refresh tokenning o'z umri (90 kun) amal qiladi; mobil ilova
foydalanuvchisi har 12 kunda qayta kirmaydi. Web va desktop uchun esa 12 kunlik
qoida saqlanadi, chunki u yerda kirish sotiladi. `expires_at` o'tgan qurilma
`is_active=False` bo'ladi va refresh ishlamaydi. Tozalash — `manage.py prune_devices`.

**`AccessCode`** (yangi) — desktop va darslik uchun kod bilan kirish.

| Maydon | Izoh |
|---|---|
| `code` | unique, 8 belgi, katta harf va raqam (chalkash `0/O`, `1/I` chiqarib tashlanadi) |
| `user` | FK, **majburiy** — shef avval o'quvchini yaratadi, keyin unga kod chiqaradi |
| `created_by` | FK → admin |
| `valid_days` | default `settings.ACCESS_CODE_DAYS` = 12 |
| `activated_at` | null — birinchi ishlatilgunicha |
| `expires_at` | `activated_at + valid_days` |
| `is_active` | Shef bekor qila oladi |

Web'dagi `Token` modelining o'rinbosari. Anonim foydalanuvchi yaratilmaydi —
shef kimga kod berayotganini biladi.

**`SocialAccount`** — mobile-back'dagidek (Apple / Google / Telegram / Email).

### 5.2 content

mobile-back'dan o'zgarishsiz ko'chadi: `Section` → `Lesson` → `Question` → `Answer`,
`Ticket` + `TicketQuestion`, `Topic`. Uch tilli ustunlar (`*_uz`, `*_ru`, `*_cry`) va
legacy PK'lar saqlanadi.

`Question` ga qo'shiladi:

| Maydon | Izoh |
|---|---|
| `is_in_web` | bool, default False. admin-panel'da bor — ma'lumot yo'qolmasin |
| `is_published` | bool. Import qilinganlar `True`, API orqali yangi yaratilgani `False` |

`is_published=False` savol o'quvchiga hech qayerda ko'rinmaydi: dars, bilet, blits,
imtihon — hammasi filtrlaydi. Shef va o'qituvchi esa ko'radi. Sabab: admin-panel
online bo'lgach har bir tahrir darhol jonli bo'ladi, yarim yozilgan savol
o'quvchiga chiqib qolmasligi kerak.

**`Blits`** (yangi) — admin-panel'dagi `blits.json`.

| Maydon | Izoh |
|---|---|
| `name_uz`, `name_ru`, `name_cry` | |
| `order` | |
| `questions` | M2M → Question, through `BlitsQuestion(order)` |
| `is_active` | |

**Variant = Bilet.** Seoul'dagi `question.json` ning `var_id` bo'yicha guruhlari
`Ticket` ga aylangan (57 × 20). Web'dagi "variant" ham shu. Alohida model kerak emas.

### 5.3 exams

**`ExamSession`** (yangi) — imtihonning server tomonidagi holati.

| Maydon | Izoh |
|---|---|
| `user` | FK |
| `mode` | 20 \| 50 |
| `started_at`, `ends_at` | `ends_at = started_at + mode["minutes"]` |
| `finished_at` | null — davom etayotgan bo'lsa |
| `score`, `pass_score` | |
| `attempt` | FK → `progress.ExamAttempt`, yakunlanganda to'ldiriladi |

**`ExamSessionQuestion`**: `session`, `question`, `order`, `answer` (FK → Answer, null),
`is_correct` (null — javob berilmagan bo'lsa).

Hozirgi `GET /api/v1/exam/generate/` savollarni beradi-yu, server qaysi savollar
berilganini eslamaydi va vaqtni nazorat qilmaydi. `ExamSession` shuni tuzatadi.

### 5.4 progress

mobile-back'dagidek: `LessonResult`, `TicketResult`, `ExamAttempt`, `QuestionAttempt`,
`SavedQuestion`, `Mistake`. Qo'shiladi:

**`BlitsResult`**: `user`, `blits`, `score`, `total`, `created_at` — `TicketResult`
bilan bir xil shakl.

`ExamAttempt` natija yozuvi bo'lib qoladi (mobil ilova undan statistika o'qiydi);
`ExamSession` esa jarayonni yuritadi va yakunda `ExamAttempt` yaratadi.

### 5.5 billing

Web'dan ko'chadi, `student` o'rniga `user`:

- **`Branch`** — `name`, `created_at`, `updated_at`
- **`StudentPayment`** — `user` (OneToOne), `amount`, `tolagani`, `created_at`
- **`PaymentReport`** — `student_payment` (FK), `paid_amount`, `date`, `comment`

### 5.6 notifications, telegramauth

mobile-back'dan o'zgarishsiz.

## 6. Autentifikatsiya va rollar

Yadro — SimpleJWT. Access 1 kun, refresh 90 kun, rotatsiya yoqilgan.
Har bir muvaffaqiyatli kirish `Device` yozuvini yaratadi; refresh'ning `jti` si
shu yozuvga bog'lanadi, shuning uchun qurilmani serverdan uzish mumkin.

**Kirish yo'llari:**

| Yo'l | Kim ishlatadi |
|---|---|
| Telefon + parol | Mobil, web |
| Kirish kodi (`AccessCode`) | Desktop darslik va imtihon (keyinchalik) |
| Apple / Google / Telegram | Mobil |

> **Xavfsizlik sharti.** Hozirgi `auth/social/` provayder tokenini tekshirmaydi
> (`views.SocialLoginView` dagi `TODO(auth)`). Bu ishda tekshiruv qo'shiladi:
> Apple identity token imzosi, Google `tokeninfo`, Telegram `hash`. Tekshiruvsiz
> ishlash imkoni olib tashlanadi.

**Ruxsat sinflari** (`common/permissions.py`):

| Sinf | Qoida |
|---|---|
| `IsStudent` | `role == student` |
| `IsTeacherOrAdmin` | `role in (teacher, admin)` |
| `IsAdminRole` | `role == admin` yoki `is_superuser` |

Kontentni o'qish barcha kirgan foydalanuvchilar uchun ochiq. To'g'ri javob
(`is_true`) test rejimida yashiriladi; `?mode=study` bilan ochiladi; `teacher` va
`admin` uchun har doim ochiq.

## 7. API

Manzil `/api/v1/`. Barcha `GET` so'rovlar `?lang=` ni qo'llaydi (`uz`/`kr`/`qq`/`ru`),
so'ng `Accept-Language`, so'ng `uz`. Bo'sh matn `uz → ru → cry` tartibida zaxiraga
o'tadi.

### 7.1 auth/

| Metod | Yo'l | Izoh |
|---|---|---|
| POST | `auth/register/` | `{phone, password, full_name?, language?}` |
| POST | `auth/login/` | `{phone, password, platform?, device_label?}` → `{user, tokens}` |
| POST | `auth/login-code/` | `{code, platform?}` → `{user, tokens}` — **yangi** |
| POST | `auth/social/` | `{provider, uid, token}` — token tekshiriladi |
| POST | `auth/token/refresh/` | |
| POST | `auth/logout/` | Joriy `Device` ni yopadi — **yangi** |
| GET/PATCH/DELETE | `auth/me/` | |
| POST | `auth/change-password/` | |
| GET | `auth/devices/` | O'z qurilmalari — **yangi** |
| DELETE | `auth/devices/{id}/` | Qurilmani uzish — **yangi** |

### 7.2 Kontent (o'qish)

| Metod | Yo'l |
|---|---|
| GET | `sections/`, `sections/{id}/` |
| GET | `lessons/?section=`, `lessons/{id}/` |
| GET | `questions/?lesson=&search=` — **yangi** |
| GET | `topics/`, `topics/{id}/` |
| GET | `tickets/`, `tickets/stats/`, `tickets/{number}/` |
| GET | `blits/`, `blits/{id}/` — **yangi** |

### 7.3 Imtihon

| Metod | Yo'l | Izoh |
|---|---|---|
| POST | `exams/start/` | `{mode: 20\|50}` → `{id, questions[], ends_at, pass_score}` |
| POST | `exams/{id}/answer/` | `{question, answer}` — oraliq saqlash |
| POST | `exams/{id}/finish/` | Serverda baholaydi → `{score, passed, items[]}` |
| GET | `exams/{id}/` | Natija |
| GET | `exams/` | Urinishlar tarixi |

`ends_at` o'tgandan keyin `answer/` `409` qaytaradi. `finish/` esa o'tgan bo'lsa ham
ishlaydi — belgilangan javoblar bo'yicha baholanadi.

### 7.4 Progress

mobile-back'dagi endpointlar saqlanadi: `progress/lesson-results/`,
`ticket-results/`, `exam-attempts/`, `mistakes/`, `mistakes/{id}/resolve/`,
`stats/`, `reset/`, `saved/`. Qo'shiladi: `progress/blits-results/`.

Ball har doim **serverda** hisoblanadi — mijoz yuborgan ballga ishonilmaydi.
Yuborish shakli o'zgarishsiz:

```jsonc
POST /api/v1/progress/lesson-results/
{"lesson": 16, "items": [{"question": 55, "answer": 210}, {"question": 56, "answer": null}]}
// -> {"id": 1, "lesson": 16, "score": 1, "total": 2, "passed": false}
```

### 7.5 Shef — `manage/` (ruxsat: `IsAdminRole`)

| Metod | Yo'l |
|---|---|
| CRUD | `manage/sections/`, `manage/lessons/`, `manage/questions/`, `manage/answers/` |
| CRUD | `manage/topics/`, `manage/tickets/`, `manage/blits/` |
| POST | `manage/{resource}/reorder/` — `{"ids": [3, 1, 2]}`, drag-and-drop uchun |
| POST | `manage/questions/{id}/image/` — multipart, WebP ga o'giriladi |
| POST | `manage/questions/{id}/audio/` — multipart |
| CRUD | `manage/users/`, `manage/branches/`, `manage/payments/`, `manage/payment-reports/` |
| POST | `manage/access-codes/` — kod chiqarish |
| POST | `manage/access-codes/{id}/revoke/` |

`manage/` javoblarida til yig'ilmaydi — uch ustun ham ochiq keladi, chunki shef
uchalasini tahrirlaydi.

### 7.6 O'qituvchi — `teacher/` (ruxsat: `IsTeacherOrAdmin`)

| Metod | Yo'l | Izoh |
|---|---|---|
| GET | `teacher/students/` | O'z filialidagi o'quvchilar |
| GET | `teacher/students/{id}/stats/` | Bitta o'quvchining natijalari va xatolari |
| GET | `teacher/stats/` | Filial kesimida umumiy ko'rsatkichlar |

O'qituvchining `branch` i bo'sh bo'lsa ro'yxat bo'sh qaytadi. `admin` esa barcha
filiallarni ko'radi, `?branch=` bilan filtrlaydi.

### 7.7 Eski nom taxalluslari

Web va darslik frontlari eski maydon nomlarini kutadi. Serializerlarda ular
qo'shimcha o'qish-uchun maydon sifatida chiqadi:

| Eski nom | Manba |
|---|---|
| `question_uz` / `question_ru` / `question_cry` | `Question.text_*` |
| `answer_uz` / `answer_ru` / `answer_cry` | `Answer.text_*` |
| `tartib` | `order` |

Taxalluslar faqat `?compat=1` so'ralganda qo'shiladi — mobil javoblari semirmaydi.

### 7.8 Deprecated

Mobil ilova do'konda turgani uchun quyidagilar ishlayveradi, lekin Swagger'da
`deprecated` deb belgilanadi:

- `GET /api/v1/exam/generate/?count=` → `exams/start/` ning o'rniga
- `POST /api/v1/progress/exam-attempts/` → `exams/{id}/finish/` ning o'rniga

### 7.9 Hujjat

`/api/docs/` (Swagger UI), `/api/redoc/`, `/api/schema/` (OpenAPI JSON) —
drf-spectacular, mobile-back'dagidek.

## 8. Django admin

Django'ning standart admin paneli saqlanadi va sozlanadi:

- Barcha modellar ro'yxatga olinadi, qidiruv va filtr bilan.
- `Question` uchun `Answer` inline, `Ticket` uchun `TicketQuestion` inline.
- `role` bo'yicha guruh va permission'lar: `teacher` guruhiga faqat progress va
  foydalanuvchini o'qish huquqi; `admin` guruhiga kontent va billing to'liq.
- Adminga kirish `is_staff` bilan, u `role` dan mustaqil.

## 9. Ko'p tillilik

`common/lang.py` o'zgarishsiz ko'chadi. Mijoz kodi → ustun: `uz→uz`, `kr→cry`,
`qq→uz`, `ru→ru`. `manage/` bundan mustasno (7.5 ga qarang).

## 10. Migratsiya

Tartib muhim.

**1-qadam — baza tiklanadi.**
`backups/avtotest_mobile_20260826_232013.sql` yangi bazaga tiklanadi. Bu
foydalanuvchilar, progress va kontentni beradi. Keyin yangi migratsiyalar
qo'llaniladi (`role`, `branch`, `Device`, `AccessCode`, `Blits`, `ExamSession`,
`billing`, `is_published`, `is_in_web`).

**2-qadam — `import_content`.**

```bash
python manage.py import_content --path ../../admin-panel/src/db [--dry-run]
```

`sections.json`, `lessons.json`, `questions.json`, `answers.json`, `blits.json` ni
o'qiydi. `variants.json` ixtiyoriy — hozir repoda yo'q (admin-panel uni
`.catch(() => [])` bilan o'qiydi), bo'lsa `Ticket` va `TicketQuestion` ga
yoziladi. Moslashtirish **id bo'yicha** — `import_seoul` legacy
PK'larni saqlagani uchun admin-panel id'lari baza id'lari bilan bir xil
(tekshirilgan: savol 55 → dars 16). Mavjud yozuv yangilanadi, yo'g'i yaratiladi.
`tartib` → `order`. `--dry-run` nima o'zgarishini ko'rsatadi, hech narsa yozmaydi.

Bazada bor-u JSON'da yo'q savol **o'chirilmaydi** — faqat hisobotda ko'rsatiladi.

**3-qadam — `import_web`.**

```bash
python manage.py import_web --database-url postgresql://...
```

Eski web bazasidan `Branch`, `Student` → `User`, `StudentPayment`, `PaymentReport`
ko'chadi. Telefon `901234567` → `+998901234567` ga keltiriladi. Telefon bo'yicha
mos `User` topilsa unga biriktiriladi, topilmasa yangi yaratiladi.

> **Parollar.** Web'da parollar ochiq matnda saqlangan. Ko'chirishda ular Django
> hash'iga o'tkaziladi. O'quvchi eski parolini ishlatishda davom etadi.

**4-qadam — media.**
`web/backend/media/` va `avtotest-mobile-back/media/` birlashtiriladi, rasmlar
WebP'ga o'giriladi (`convert_images_to_webp` buyrug'i, web'dagidan ko'chiriladi).

Har bir buyruq idempotent: ikki marta ishlatilsa natija o'zgarmaydi.

## 11. Sinov strategiyasi

pytest + pytest-django. TDD: har bir endpoint uchun test avval yoziladi.

Majburiy qamrov:

| Soha | Nimani tekshiradi |
|---|---|
| Rollar | `student` `manage/` ga kira olmaydi; `teacher` boshqa filial o'quvchisini ko'rmaydi |
| Baholash | Server ballni o'zi hisoblaydi; mijoz yuborgan `score` e'tiborga olinmaydi |
| Imtihon | `ends_at` dan keyin javob qabul qilinmaydi; `finish/` bir marta ishlaydi |
| Qurilma | Limitdan oshganda 403; `expires_at` o'tgach refresh ishlamaydi |
| Kirish kodi | Bir marta faollashadi; bekor qilingan kod ishlamaydi; muddati o'tgani ishlamaydi |
| Til | `?lang=kr` → `_cry`; bo'sh matn `uz → ru → cry` ga tushadi |
| Yashirish | Test rejimida `is_true` qaytmaydi; `?mode=study` da qaytadi |
| `is_published` | Nashr etilmagan savol o'quvchiga hech qayerda ko'rinmaydi |
| Import | Kichik fixture bilan: id bo'yicha moslashtirish, idempotentlik, `--dry-run` |

## 12. Deploy

`docker-compose.yml` saqlanadi va kengaytiriladi: Postgres 15, gunicorn, media
volume. Baza faqat `DATABASE_URL` orqali sozlanadi (mobile-back'dagi qoida).

`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` — muhit
o'zgaruvchilaridan. Hozirgi `avtotest-online/backend/config/settings.py` dagi
qattiq yozilgan `SECRET_KEY`, `ALLOWED_HOSTS = ['*']` va
`CORS_ALLOW_ALL_ORIGINS = True` olib tashlanadi.

## 13. Qamrovdan tashqari

- Desktop ilovalarni ulash va ulardagi `db.enc` ni olib tashlash
- Mobil, web va admin-panel frontlarini yangi API'ga qayta ulash
- Offline snapshot / kontent versiyalash
- Octagon (1v1 quiz-battle) — mobil ekranda bor, backendi hali yo'q
- PRO obuna to'lovi va to'lov tizimi integratsiyasi

Ular alohida bosqichlarda, o'z speclari bilan.

## 14. Ish yakunida beriladigan hisobot

Backend tayyor bo'lgach, har bir front uchun quyidagilar yoziladi: qaysi
endpointlarga ulanishi, qaysi maydonlar o'zgargani, `?compat=1` kerakmi-yo'qmi,
auth qanday o'tishi va ulash uchun qancha ish borligi.
