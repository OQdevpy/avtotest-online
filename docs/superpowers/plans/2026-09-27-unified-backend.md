# Yagona backend — implementatsiya rejasi

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** `avtotest-online/backend` ni AvtoTest'ning yagona markaziy backendiga aylantirish — bitta baza, bitta auth, bitta kontent manbai, bitta API.

**Architecture:** `avtotest-mobile-back` kodi poydevor sifatida ko'chiriladi. Ustiga rollar, qurilma sessiyasi, kirish kodi, blits, imtihon sessiyasi, billing, shef va o'qituvchi API'lari qo'shiladi. Modulli monolit: har bir app bitta sohaga javob beradi. Mavjud mobil endpointlar buzilmaydi — ilova do'konda turibdi.

**Tech Stack:** Python 3.12+, Django 6.0.7, DRF 3.17.1, SimpleJWT 5.5.1, PostgreSQL, drf-spectacular, Pillow, pytest + pytest-django.

**Spec:** `docs/superpowers/specs/2026-09-27-unified-backend-design.md`

## Global Constraints

Har bir taskning talablariga quyidagilar avtomatik kiradi:

- Python 3.12+, Django 6.0.7 — eskiroq versiyada ishlamaydi.
- Baza **faqat** `DATABASE_URL` orqali sozlanadi; o'zgaruvchi bo'lmasa ilova ishga tushmaydi.
- Ball **har doim serverda** hisoblanadi. Mijoz yuborgan `score` e'tiborga olinmaydi.
- `is_published=False` savol o'quvchiga **hech bir yo'l orqali** ko'rinmaydi. `teacher` va `admin` ko'radi.
- To'g'ri javob (`is_true`) test rejimida qaytmaydi; `?mode=study` da qaytadi; `teacher`/`admin` uchun har doim qaytadi.
- Til: mijoz kodi → ustun `uz→uz`, `kr→cry`, `cry→cry`, `qq→uz`, `ru→ru`. Bo'sh matn `uz → ru → cry` tartibida zaxiraga tushadi. `manage/` bundan mustasno — uch ustun ham ochiq keladi.
- Telefon har doim `+998XXXXXXXXX` ko'rinishiga keltiriladi (`accounts.models.normalize_phone`).
- `settings.MAX_DEVICES_PER_PLATFORM = {"mobile": 2, "web": 1, "desktop": 1}`
- `settings.SESSION_DAYS = {"mobile": None, "web": 12, "desktop": 12}` — `None` = muddat yo'q.
- `settings.ACCESS_CODE_DAYS = 12`
- `settings.EXAM_MODES = {20: {"questions": 20, "minutes": 25, "pass_score": 18}, 50: {"questions": 50, "minutes": 45, "pass_score": 46}}`
- `settings.LESSON_PASS_RATIO = 0.7`, `settings.LESSON_GREEN_RATIO = 0.9`
- Deprecated endpointlar (`GET /api/v1/exam/generate/`, `POST /api/v1/progress/exam-attempts/`) **ishlashda davom etadi**; faqat Swagger'da `deprecated` belgisi.
- Har bir management buyrug'i idempotent: ikki marta ishlatilsa natija o'zgarmaydi.

## Review Focus

Spec talab qiladi-yu, oddiy task testlari o'tkazib yuborishi mumkin bo'lgan holatlar. Har biri o'z taskida test bilan qoplanadi:

1. **Nashr etilmagan savol sizib chiqishi** — `is_published=False` savol dars, bilet, blits, imtihon va qidiruv — beshala yo'lning birortasidan o'quvchiga yetib bormasligi. → Task 6
2. **Imtihonni ikki marta yakunlash** — `finish/` takroran chaqirilsa ikkinchi `ExamAttempt` yaratilmasligi va ball o'zgarmasligi; aks holda statistika buziladi. → Task 11
3. **O'qituvchining begona filialga qarashi** — boshqa filial o'quvchisining id'si bilan so'rov yuborilganda ma'lumot qaytmasligi. → Task 13
4. **Muddati o'tgan qurilmaning cheksiz uzayishi** — `expires_at` o'tgach refresh ishlamasligi; aks holda web'da sotilgan 12 kunlik kirish cheksiz aylanadi. → Task 3
5. **`import_web` da telefon to'qnashuvi** — web'dagi 9 xonali raqam `+998…` ga aylanganda bazada allaqachon shunday foydalanuvchi bo'lsa, uning paroli va progressi ustiga yozilmasligi. → Task 16

---

## Fayl tuzilishi

```
backend/
  config/         settings.py, urls.py, api_urls.py, asgi.py, wsgi.py
  common/         lang.py, models.py, pagination.py, permissions.py, views.py
  apps/
    accounts/     models.py, serializers.py, views.py, urls.py, admin.py,
                  devices.py, social.py, teacher_views.py, teacher_urls.py
    content/      models.py, serializers.py, views.py, urls.py, admin.py,
                  manage_serializers.py, manage_views.py, manage_urls.py,
                  management/commands/{import_seoul,import_content}.py
    exams/        models.py, serializers.py, views.py, urls.py, admin.py, grading.py
    progress/     models.py, serializers.py, views.py, urls.py, admin.py, services.py
    billing/      models.py, serializers.py, views.py, urls.py, admin.py,
                  management/commands/import_web.py
    notifications/  (mobile-back'dan o'zgarishsiz)
    telegramauth/   (mobile-back'dan o'zgarishsiz)
  tests/          conftest.py, test_*.py
  media/, seed_data/
  pytest.ini, requirements.txt, Dockerfile, docker-compose.yml, manage.py
```

O'qituvchi API'si `apps/accounts/` ichida yashaydi (resurs — foydalanuvchilar), statistikani `apps/progress/services.py` dan oladi. Spec'dagi app ro'yxati o'zgarmaydi.

---

# FAZA 1 — Poydevor

### Task 1: Loyihani ko'chirish va sinov muhiti

**Files:**
- Create: `backend/pytest.ini`, `backend/tests/conftest.py`, `backend/tests/test_smoke.py`
- Copy: `avtotest-mobile-back/{apps,common,config}/` → `backend/{apps,common,config}/`
- Delete: `backend/students/`, `backend/content/` (eski, `apps/content/` bilan almashadi)
- Modify: `backend/requirements.txt`, `backend/config/settings.py`

**Interfaces:**
- Consumes: —
- Produces: ishlaydigan Django loyihasi; `apps.accounts.models.User` (`AUTH_USER_MODEL`), `apps.content.models.{Section,Lesson,Question,Answer,Ticket,TicketQuestion,Topic}`, `common.lang.{resolve_lang,pick,TranslatedField,LangSerializerContextMixin}`, `common.pagination.DefaultPagination`. Pytest fixture'lari: `api` (DRF `APIClient`), `student`, `teacher`, `admin_user`, `auth` (`auth(client, user)` — JWT sarlavhasini o'rnatadi).

- [ ] **Step 1: Kodni ko'chirish**

`avtotest-mobile-back` dan `apps/`, `common/`, `config/` papkalarini `backend/` ga nusxalang. `backend/students/` va eski `backend/content/` ni o'chiring. `backend/media/` va `backend/seed_data/` joyida qoladi.

- [ ] **Step 2: `requirements.txt` va `pytest.ini`**

`requirements.txt` — mobile-back'dagi ro'yxat + `pytest==8.3.4`, `pytest-django==4.9.0`.

`pytest.ini`:
```ini
[pytest]
DJANGO_SETTINGS_MODULE = config.settings
python_files = test_*.py
```

- [ ] **Step 3: `settings.py` ni muhitga bog'lash**

`SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS` — barchasi muhit o'zgaruvchisidan. Qattiq yozilgan kalit, `ALLOWED_HOSTS = ['*']` va `CORS_ALLOW_ALL_ORIGINS = True` olib tashlanadi. Global Constraints'dagi barcha `settings.*` qiymatlari shu faylga yoziladi.

- [ ] **Step 4: `tests/conftest.py` fixture'larini yozish**

`api`, `student`, `teacher`, `admin_user`, `auth` fixture'lari. Rol maydoni hali yo'q — `teacher`/`admin_user` hozircha `is_staff` bilan ajratiladi, Task 2 da `role` ga o'tkaziladi.

- [ ] **Step 5: Smoke testni yozish**

```python
def test_sections_requires_auth(api):
    assert api.get("/api/v1/sections/").status_code == 401

def test_sections_returns_list_for_authenticated_user(api, student, auth):
    auth(api, student)
    assert api.get("/api/v1/sections/").status_code == 200
```

- [ ] **Step 6: Testlarni ishga tushirish**

Run: `pytest tests/test_smoke.py -v`
Expected: PASS (ikkalasi)

- [ ] **Step 7: Commit**

```bash
git add backend
git commit -m "feat: mobile backend kodini yagona backend poydevori sifatida ko'chirish"
```

---

### Task 2: Rollar va ruxsat sinflari

**Files:**
- Modify: `backend/apps/accounts/models.py`, `backend/apps/accounts/serializers.py`, `backend/tests/conftest.py`
- Create: `backend/common/permissions.py`, `backend/apps/accounts/migrations/000X_user_role.py`, `backend/tests/test_permissions.py`

**Interfaces:**
- Consumes: Task 1 — `User`
- Produces:
  ```python
  # apps/accounts/models.py
  class User.Role(models.TextChoices):
      STUDENT = "student"; TEACHER = "teacher"; ADMIN = "admin"
  User.role: str            # default Role.STUDENT
  User.is_teacher: bool     # property, role in (teacher, admin)
  User.is_content_admin: bool  # property, role == admin yoki is_superuser

  # common/permissions.py
  class IsStudent(BasePermission)
  class IsTeacherOrAdmin(BasePermission)
  class IsAdminRole(BasePermission)
  ```

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_new_user_defaults_to_student_role(student):
    assert student.role == "student"

def test_is_content_admin_true_for_superuser(django_user_model):
    u = django_user_model.objects.create_superuser("+998901112233", "x")
    assert u.is_content_admin

def test_is_teacher_false_for_student(student):
    assert not student.is_teacher

def test_admin_role_permission_rejects_student(rf, student):
    request = rf.get("/"); request.user = student
    assert not IsAdminRole().has_permission(request, None)
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_permissions.py -v`
Expected: FAIL — `role` maydoni yo'q, `common.permissions` moduli yo'q

- [ ] **Step 3: `User.Role`, `role`, `is_teacher`, `is_content_admin` ni qo'shish**

`role` — `CharField(max_length=10, choices=Role.choices, default=Role.STUDENT, db_index=True)`. Migratsiya yaratiladi; mavjud qatorlar `student` bo'ladi.

- [ ] **Step 4: `common/permissions.py` ni yozish**

Uchala sinf `BasePermission` dan; `has_permission` avval `request.user.is_authenticated` ni tekshiradi.

- [ ] **Step 5: `conftest.py` fixture'larini `role` ga o'tkazish**

`teacher` → `role="teacher"`, `admin_user` → `role="admin"`.

- [ ] **Step 6: Testlar o'tishini tasdiqlash**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/apps/accounts backend/common/permissions.py backend/tests
git commit -m "feat: foydalanuvchi rollari va ruxsat sinflari"
```

---

### Task 3: Device — qurilma sessiyasi va muddat

**Files:**
- Create: `backend/apps/accounts/devices.py`, `backend/apps/accounts/management/commands/prune_devices.py`, `backend/tests/test_devices.py`
- Modify: `backend/apps/accounts/{models,serializers,views,urls}.py`, `backend/config/settings.py`

**Interfaces:**
- Consumes: Task 2 — `User`
- Produces:
  ```python
  # apps/accounts/models.py
  class Device(models.Model):
      user, platform, refresh_jti (unique), label, created_at, last_seen, expires_at, is_active
      @property is_expired(self) -> bool

  # apps/accounts/devices.py
  class DeviceLimitReached(Exception)
  def register_device(user, platform: str, label: str, refresh) -> Device
      # limit oshgan bo'lsa DeviceLimitReached ko'taradi
  def device_for_refresh(jti: str) -> Device | None
      # yo'q, faol emas yoki muddati o'tgan bo'lsa None
  ```
  Yangi endpointlar: `POST auth/logout/`, `GET auth/devices/`, `DELETE auth/devices/{id}/`.
  `LoginView` va `SocialLoginView` `{platform?, device_label?}` qabul qiladi (`platform` default `"mobile"`).

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_login_creates_device(api, student):
    r = api.post("/api/v1/auth/login/", {"phone": student.phone, "password": "pass1234",
                                         "platform": "web"}, format="json")
    assert r.status_code == 200
    assert Device.objects.filter(user=student, platform="web").count() == 1

def test_second_web_login_is_rejected(api, student, logged_in_web):
    r = api.post("/api/v1/auth/login/", {"phone": student.phone, "password": "pass1234",
                                         "platform": "web"}, format="json")
    assert r.status_code == 403
    assert "qurilma" in r.json()["detail"].lower()

def test_mobile_allows_two_devices(api, student):
    ...  # ikki marta platform="mobile" bilan kirish -> ikkalasi ham 200

# Review Focus #4
def test_refresh_fails_after_device_expires(api, student, freezer):
    tokens = login(api, student, platform="web")
    Device.objects.filter(user=student).update(expires_at=timezone.now() - timedelta(seconds=1))
    r = api.post("/api/v1/auth/token/refresh/", {"refresh": tokens["refresh"]}, format="json")
    assert r.status_code == 401

def test_mobile_device_has_no_expiry(api, student):
    login(api, student, platform="mobile")
    assert Device.objects.get(user=student).expires_at is None

def test_logout_deactivates_device(api, student, auth):
    ...  # logout -> is_active False, refresh 401
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_devices.py -v`
Expected: FAIL — `Device` modeli yo'q

- [ ] **Step 3: `Device` modeli va migratsiya**

`expires_at` — `SESSION_DAYS[platform]` `None` bo'lsa `null`, aks holda `created_at + N kun`.

- [ ] **Step 4: `devices.py` servis funksiyalarini yozish**

`register_device` limitni `settings.MAX_DEVICES_PER_PLATFORM` dan oladi; `user.max_devices` to'ldirilgan bo'lsa u barcha platformalar uchun ustun turadi. Limit oshganda eng eskisi o'chirilmaydi — `DeviceLimitReached` ko'tariladi.

- [ ] **Step 5: `User.max_devices` maydonini qo'shish**

`PositiveSmallIntegerField(null=True, blank=True)`.

- [ ] **Step 6: Login/refresh/logout view'larini ulash**

`LoginView` va `SocialLoginView` `register_device` ni chaqiradi, `DeviceLimitReached` → `403 {"detail": "Ushbu hisob allaqachon boshqa qurilmada ochiq."}`.

`TokenRefreshView` o'rniga `DeviceAwareTokenRefreshView`: refresh `jti` si bo'yicha `device_for_refresh` `None` qaytarsa `401`. Rotatsiya yoqilgani uchun yangi `jti` `Device` ga yoziladi va `last_seen` yangilanadi.

- [ ] **Step 7: `prune_devices` buyrug'ini yozish**

Muddati o'tgan `Device` larni `is_active=False` qiladi. Idempotent.

- [ ] **Step 8: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_devices.py -v`
Expected: PASS

- [ ] **Step 9: Commit**

```bash
git add backend/apps/accounts backend/config/settings.py backend/tests/test_devices.py
git commit -m "feat: qurilma sessiyasi, limit va muddat nazorati"
```

---

### Task 4: AccessCode — kod bilan kirish

**Files:**
- Create: `backend/tests/test_access_codes.py`
- Modify: `backend/apps/accounts/{models,serializers,views,urls}.py`

**Interfaces:**
- Consumes: Task 2 (`IsAdminRole`), Task 3 (`register_device`)
- Produces:
  ```python
  # apps/accounts/models.py
  class AccessCode(models.Model):
      code (unique, 8), user (FK, majburiy), created_by (FK), valid_days,
      activated_at, expires_at, is_active
      @classmethod generate(cls, *, user, created_by, valid_days=None) -> "AccessCode"
      @property is_usable(self) -> bool   # is_active va (activated_at is None yoki expires_at > now)
      def activate(self) -> None          # activated_at/expires_at ni bir marta o'rnatadi
  ```
  Endpointlar: `POST auth/login-code/` `{code, platform?}` → `{user, tokens}`;
  `POST manage/access-codes/` (admin), `POST manage/access-codes/{id}/revoke/` (admin).

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_generated_code_is_eight_unambiguous_chars(student, admin_user):
    c = AccessCode.generate(user=student, created_by=admin_user)
    assert len(c.code) == 8
    assert not set(c.code) & set("O0I1")

def test_login_with_code_returns_tokens_and_activates(api, student, admin_user):
    c = AccessCode.generate(user=student, created_by=admin_user)
    r = api.post("/api/v1/auth/login-code/", {"code": c.code, "platform": "desktop"}, format="json")
    assert r.status_code == 200 and "access" in r.json()["tokens"]
    c.refresh_from_db()
    assert c.activated_at is not None
    assert c.expires_at == c.activated_at + timedelta(days=12)

def test_second_login_keeps_original_expiry(api, student, admin_user):
    ...  # ikkinchi kirish activated_at ni o'zgartirmaydi

def test_revoked_code_rejected(api, student, admin_user):
    ...  # is_active=False -> 401

def test_expired_code_rejected(api, student, admin_user):
    ...  # expires_at o'tgan -> 401

def test_unknown_code_rejected(api):
    assert api.post("/api/v1/auth/login-code/", {"code": "ZZZZZZZZ"}, format="json").status_code == 401

def test_student_cannot_create_access_code(api, student, auth):
    auth(api, student)
    assert api.post("/api/v1/manage/access-codes/", {"user": student.id}, format="json").status_code == 403
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_access_codes.py -v`
Expected: FAIL — `AccessCode` yo'q

- [ ] **Step 3: `AccessCode` modeli va migratsiya**

Alifbo: `ABCDEFGHJKLMNPQRSTUVWXYZ23456789` (chalkash `O/0`, `I/1` yo'q). `generate` unikal kod topilgunicha qayta uradi.

- [ ] **Step 4: `auth/login-code/` view'ini yozish**

Kodni topadi → `is_usable` bo'lmasa `401` → `activate()` → `register_device(platform default "desktop")` → JWT qaytaradi.

- [ ] **Step 5: `manage/access-codes/` CRUD va `revoke` action**

`IsAdminRole`. `revoke` → `is_active=False`.

- [ ] **Step 6: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_access_codes.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/apps/accounts backend/tests/test_access_codes.py
git commit -m "feat: kirish kodi bilan autentifikatsiya"
```

---

### Task 5: Ijtimoiy kirish tokenini tekshirish

**Files:**
- Create: `backend/apps/accounts/social.py`, `backend/tests/test_social_auth.py`
- Modify: `backend/apps/accounts/views.py` (`SocialLoginView`), `backend/config/settings.py`

**Interfaces:**
- Consumes: Task 3 (`register_device`)
- Produces:
  ```python
  # apps/accounts/social.py
  class SocialVerificationError(Exception)
  def verify_social_token(provider: str, token: str, uid: str) -> dict
      # {"uid": str, "email": str} qaytaradi; nomuvofiqlikda SocialVerificationError
  ```
  Sozlamalar: `APPLE_BUNDLE_ID`, `GOOGLE_CLIENT_IDS`, `TELEGRAM_BOT_TOKEN`.

Bu spec'dagi `TODO(auth)` ni yopadi: tekshiruvsiz ishlash imkoni butunlay olib tashlanadi.

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_apple_token_with_wrong_audience_rejected(): ...
def test_apple_token_with_bad_signature_rejected(): ...
def test_google_tokeninfo_mismatched_sub_rejected(httpx_mock): ...
def test_telegram_hash_mismatch_rejected(): ...
def test_valid_google_token_returns_uid_and_email(httpx_mock): ...

def test_social_login_rejects_unverified_token(api):
    r = api.post("/api/v1/auth/social/",
                 {"provider": "google", "uid": "123", "token": "bad"}, format="json")
    assert r.status_code == 401
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_social_auth.py -v`
Expected: FAIL — `apps.accounts.social` yo'q

- [ ] **Step 3: `verify_social_token` ni yozish**

- **Apple:** `https://appleid.apple.com/auth/keys` dan JWK, `PyJWT` bilan imzo va `aud == APPLE_BUNDLE_ID`, `iss == https://appleid.apple.com` tekshiriladi. Kalitlar 24 soat keshlanadi.
- **Google:** `https://oauth2.googleapis.com/tokeninfo?id_token=` ga `httpx` so'rovi; `aud` `GOOGLE_CLIENT_IDS` ichida va `sub == uid` bo'lishi shart.
- **Telegram:** `data_check_string` ning HMAC-SHA256 i (kalit — `sha256(TELEGRAM_BOT_TOKEN)`) `hash` bilan mos kelishi, `auth_date` 24 soatdan eski emasligi.

- [ ] **Step 4: `SocialLoginView` ni ulash**

`verify_social_token` ni chaqiradi; `SocialVerificationError` → `401`. Tekshiruvdan o'tgan `uid` bo'yicha `SocialAccount` topiladi yoki yaratiladi.

- [ ] **Step 5: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_social_auth.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/accounts backend/config/settings.py backend/tests/test_social_auth.py
git commit -m "feat: Apple/Google/Telegram tokenini tekshirish"
```

---

# FAZA 2 — Kontent

### Task 6: `is_published` va `is_in_web`

**Files:**
- Modify: `backend/apps/content/{models,views,serializers}.py`
- Create: `backend/tests/test_published_filter.py`

**Interfaces:**
- Consumes: Task 1 — `Question`
- Produces:
  ```python
  # apps/content/models.py
  Question.is_in_web: bool      # default False
  Question.is_published: bool   # default False; migratsiya mavjud qatorlarni True qiladi
  Question.published: Manager   # is_published=True bilan filtrlangan qo'shimcha manager
  ```
  `Question.objects` o'zgarmaydi — shef va o'qituvchi yo'llari undan foydalanadi.

- [ ] **Step 1: Failing testlarni yozish — Review Focus #1**

Beshala yo'l alohida tekshiriladi:
```python
@pytest.fixture
def hidden_question(lesson, ticket, blits):
    ...  # is_published=False, dars/bilet/blitsga biriktirilgan

def test_unpublished_hidden_from_lesson_detail(api, student, auth, hidden_question): ...
def test_unpublished_hidden_from_ticket_detail(api, student, auth, hidden_question): ...
def test_unpublished_hidden_from_blits_detail(api, student, auth, hidden_question): ...
def test_unpublished_hidden_from_exam_generate(api, student, auth, hidden_question): ...
def test_unpublished_hidden_from_question_search(api, student, auth, hidden_question): ...

def test_teacher_sees_unpublished(api, teacher, auth, hidden_question): ...
def test_migration_marks_existing_questions_published(): ...

# Spec §6: to'g'ri javob teacher va admin uchun har doim ochiq
def test_teacher_sees_is_true_without_study_mode(api, teacher, auth, question):
    body = api.get(f"/api/v1/lessons/{question.lesson_id}/").json()
    assert "is_true" in body["questions"][0]["answers"][0]

def test_student_never_sees_is_true_without_study_mode(api, student, auth, question):
    body = api.get(f"/api/v1/lessons/{question.lesson_id}/").json()
    assert "is_true" not in body["questions"][0]["answers"][0]
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_published_filter.py -v`
Expected: FAIL — maydonlar yo'q

- [ ] **Step 3: Maydonlar va migratsiya**

Ma'lumot migratsiyasi: barcha mavjud qatorlar `is_published=True`.

- [ ] **Step 4: O'qish yo'llarini `Question.published` ga o'tkazish**

`LessonDetailView`, `TicketDetailView`, `TopicDetailView`, `ExamGenerateView`, yangi `QuestionListView`, `BlitsDetailView`. `request.user.is_teacher` bo'lsa `Question.objects` ishlatiladi.

Tanlovni bitta joyda saqlash uchun `apps/content/views.py` da ikki yordamchi:
```python
def visible_questions(request):        # -> QuerySet[Question]
def question_serializer_for(request):  # -> type[QuestionSerializer | QuestionPublicSerializer]
    # QuestionSerializer (is_true bilan) agar ?mode=study yoki request.user.is_teacher
```
`question_serializer_for` `?mode=study` tekshiruvini bitta joyga yig'adi — hozir u `ExamGenerateView` da alohida takrorlangan.

- [ ] **Step 5: Testlar o'tishini tasdiqlash**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/content backend/tests/test_published_filter.py
git commit -m "feat: savol nashr holati va o'quvchidan yashirish"
```

> Task 6 ning blits va imtihon testlari Task 7 va Task 11 dan keyin ishlaydi. Agar Task 6 ularning oldidan bajarilsa, o'sha ikki testni `pytest.mark.xfail(strict=True)` bilan belgilang va tegishli taskda olib tashlang.

---

### Task 7: Blits modeli va o'qish API'si

**Files:**
- Modify: `backend/apps/content/{models,serializers,views,urls,admin}.py`
- Create: `backend/tests/test_blits.py`

**Interfaces:**
- Consumes: Task 6 — `visible_questions`
- Produces:
  ```python
  # apps/content/models.py
  class Blits(models.Model):
      name_uz, name_ru, name_cry, order, is_active
      questions: M2M -> Question, through="BlitsQuestion"
  class BlitsQuestion(models.Model):
      blits, question, order      # unique_together (blits, question)

  # apps/content/serializers.py
  class BlitsSerializer          # id, name, order, question_count
  class BlitsDetailSerializer    # + questions (QuestionPublicSerializer)
  ```
  Endpointlar: `GET blits/`, `GET blits/{id}/`.

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_blits_list_returns_name_in_requested_language(api, student, auth, blits):
    r = api.get("/api/v1/blits/?lang=kr"); assert r.json()["results"][0]["name"] == blits.name_cry

def test_blits_list_hides_inactive(api, student, auth): ...
def test_blits_detail_returns_questions_in_order(api, student, auth, blits): ...
def test_blits_detail_hides_correct_answer(api, student, auth, blits):
    q = api.get(f"/api/v1/blits/{blits.id}/").json()["questions"][0]
    assert "is_true" not in q["answers"][0]

def test_blits_detail_study_mode_shows_correct_answer(api, student, auth, blits): ...
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_blits.py -v`
Expected: FAIL — `Blits` yo'q

- [ ] **Step 3: Modellar va migratsiya**

- [ ] **Step 4: Serializer va view'lar**

`LangSerializerContextMixin` ishlatiladi. `question_count` — `visible_questions` bo'yicha hisoblanadi.

- [ ] **Step 5: Django admin'ga ro'yxatdan o'tkazish**

`BlitsQuestion` inline bilan.

- [ ] **Step 6: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_blits.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/apps/content backend/tests/test_blits.py
git commit -m "feat: blits modeli va o'qish API'si"
```

---

### Task 8: `questions/` ro'yxat endpointi

**Files:**
- Modify: `backend/apps/content/{views,urls}.py`
- Create: `backend/tests/test_question_list.py`

**Interfaces:**
- Consumes: Task 6 — `visible_questions`
- Produces: `GET questions/?lesson=&section=&search=` — `DefaultPagination` bilan sahifalanadi, `QuestionPublicSerializer` (yoki `?mode=study` da `QuestionSerializer`).

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_filters_by_lesson(api, student, auth): ...
def test_search_matches_any_language_column(api, student, auth):
    # ?search= uz, ru va cry ustunlari bo'yicha qidiradi
def test_results_are_paginated(api, student, auth): ...
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_question_list.py -v`
Expected: FAIL — 404

- [ ] **Step 3: `QuestionListView` ni yozish**

`search` — `text_uz`, `text_ru`, `text_cry` bo'yicha `icontains` `Q` birlashmasi.

- [ ] **Step 4: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_question_list.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/content backend/tests/test_question_list.py
git commit -m "feat: savollar ro'yxati va qidiruv endpointi"
```

---

### Task 9: `manage/` — kontent CRUD va tartiblash

**Files:**
- Create: `backend/apps/content/manage_serializers.py`, `backend/apps/content/manage_views.py`, `backend/apps/content/manage_urls.py`, `backend/tests/test_manage_content.py`
- Modify: `backend/config/api_urls.py`

**Interfaces:**
- Consumes: Task 2 (`IsAdminRole`), Task 7 (`Blits`)
- Produces:
  ```python
  # apps/content/manage_views.py — barchasi ModelViewSet, permission_classes = [IsAdminRole]
  ManageSectionViewSet, ManageLessonViewSet, ManageQuestionViewSet,
  ManageAnswerViewSet, ManageTopicViewSet, ManageTicketViewSet, ManageBlitsViewSet

  class ReorderMixin:
      @action(detail=False, methods=["post"])
      def reorder(self, request)   # {"ids": [3, 1, 2]} -> order 0,1,2
  ```
  `manage/` serializerlari til yig'maydi — `*_uz`, `*_ru`, `*_cry` uchalasi ham ochiq keladi va yoziladi. `manage/questions/` javobida `answers` ichma-ich keladi.

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_student_cannot_list_manage_questions(api, student, auth):
    auth(api, student); assert api.get("/api/v1/manage/questions/").status_code == 403

def test_teacher_cannot_create_question(api, teacher, auth): ...  # 403

def test_admin_creates_question_unpublished_by_default(api, admin_user, auth, lesson):
    r = api.post("/api/v1/manage/questions/",
                 {"lesson": lesson.id, "text_uz": "Savol", "text_ru": "", "text_cry": ""},
                 format="json")
    assert r.status_code == 201 and r.json()["is_published"] is False

def test_manage_serializer_exposes_all_three_languages(api, admin_user, auth, question):
    body = api.get(f"/api/v1/manage/questions/{question.id}/").json()
    assert {"text_uz", "text_ru", "text_cry"} <= body.keys()

def test_reorder_sets_order_by_position(api, admin_user, auth, lesson):
    api.post("/api/v1/manage/lessons/reorder/", {"ids": [3, 1, 2]}, format="json")
    assert [l.id for l in Lesson.objects.order_by("order")] == [3, 1, 2]

def test_reorder_rejects_unknown_id(api, admin_user, auth):
    assert api.post("/api/v1/manage/lessons/reorder/", {"ids": [999]}, format="json").status_code == 400
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_manage_content.py -v`
Expected: FAIL — 404

- [ ] **Step 3: `manage_serializers.py` ni yozish**

Har bir model uchun `ModelSerializer`, `fields = "__all__"`. `TranslatedField` ishlatilmaydi.

- [ ] **Step 4: `ReorderMixin` va viewset'larni yozish**

`reorder` bitta tranzaksiyada `bulk_update` qiladi; ro'yxatdagi biror id topilmasa `400` va hech narsa yozilmaydi.

- [ ] **Step 5: `manage_urls.py` ni `api_urls.py` ga ulash**

`path("manage/", include("apps.content.manage_urls"))`.

- [ ] **Step 6: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_manage_content.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/apps/content backend/config/api_urls.py backend/tests/test_manage_content.py
git commit -m "feat: shef uchun kontent CRUD va tartiblash API'si"
```

---

### Task 10: `manage/` — rasm va audio yuklash

**Files:**
- Create: `backend/apps/content/media.py`, `backend/apps/content/management/commands/convert_images_to_webp.py`, `backend/tests/test_manage_media.py`
- Modify: `backend/apps/content/manage_views.py`

**Interfaces:**
- Consumes: Task 9 — `ManageQuestionViewSet`
- Produces:
  ```python
  # apps/content/media.py
  class UnreadableImage(Exception)
  def to_webp(source, dest_name: str) -> str
      # rasmni WEBP quality=85 bilan MEDIA_ROOT/images/ ga yozadi,
      # nisbiy yo'lni qaytaradi ("images/<dest_name>.webp");
      # ochib bo'lmasa UnreadableImage

  # ManageQuestionViewSet ichida
  @action(detail=True, methods=["post"], parser_classes=[MultiPartParser])
  def image(self, request, pk)   # -> {"image": "images/<name>.webp"}
  @action(detail=True, methods=["post"], parser_classes=[MultiPartParser])
  def audio(self, request, pk)   # -> {"audio": "audio/<name>.<ext>"}
  ```
  Buyruq: `python manage.py convert_images_to_webp [--dry-run]` — spec §10 ning
  4-qadami. `MEDIA_ROOT/images/` dagi WebP bo'lmagan rasmlarni o'giradi va
  `Question.image` / `Question.explanation_image` yo'llarini yangilaydi. `to_webp`
  ni qayta ishlatadi, idempotent (allaqachon `.webp` bo'lgani o'tkazib yuboriladi).

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_uploaded_png_is_stored_as_webp(api, admin_user, auth, question, png_bytes):
    r = api.post(f"/api/v1/manage/questions/{question.id}/image/",
                 {"file": SimpleUploadedFile("a.png", png_bytes, "image/png")})
    assert r.status_code == 200 and r.json()["image"].endswith(".webp")
    question.refresh_from_db(); assert (MEDIA_ROOT / question.image).exists()

def test_non_image_upload_rejected(api, admin_user, auth, question):
    ...  # 400

def test_student_cannot_upload(api, student, auth, question):
    ...  # 403

def test_replacing_image_removes_previous_file(api, admin_user, auth, question): ...

def test_bulk_command_converts_png_and_updates_paths(db, question_with_png):
    call_command("convert_images_to_webp")
    question_with_png.refresh_from_db()
    assert question_with_png.image.endswith(".webp")

def test_bulk_command_is_idempotent(db, question_with_png): ...
def test_bulk_dry_run_changes_nothing(db, question_with_png): ...
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_manage_media.py -v`
Expected: FAIL — 404 va buyruq yo'q

- [ ] **Step 3: `media.py` dagi `to_webp` ni yozish**

Pillow: `Image.open(source).save(dest, "WEBP", quality=85)`. Fayl nomi — `question.id` va qisqa tasodifiy qo'shimchadan (mijozdagi kesh yangilanishi uchun).

- [ ] **Step 4: `image` va `audio` action'larini yozish**

`to_webp` ni chaqiradi; `UnreadableImage` → `400`. Eski fayl almashtirilganda o'chiriladi.

- [ ] **Step 5: `convert_images_to_webp` buyrug'ini yozish**

- [ ] **Step 6: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_manage_media.py -v`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add backend/apps/content backend/tests/test_manage_media.py
git commit -m "feat: rasm va audio yuklash hamda WebP ga ommaviy o'girish"
```

---

# FAZA 3 — Imtihon va progress

### Task 11: ExamSession — imtihon sessiyasi va baholash

**Files:**
- Create: `backend/apps/exams/` (`__init__.py`, `apps.py`, `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `grading.py`, `migrations/`), `backend/tests/test_exams.py`
- Modify: `backend/config/{settings,api_urls}.py`, `backend/apps/content/views.py` (`ExamGenerateView` — `deprecated` belgisi)

**Interfaces:**
- Consumes: Task 6 (`visible_questions`), Task 1 (`progress.ExamAttempt`)
- Produces:
  ```python
  # apps/exams/models.py
  class ExamSession(models.Model):
      user, mode, started_at, ends_at, finished_at, score, pass_score
      attempt: FK -> progress.ExamAttempt, null
      @property is_open(self) -> bool     # finished_at is None va ends_at > now
  class ExamSessionQuestion(models.Model):
      session, question, order, answer (FK Answer, null), is_correct (null)

  # apps/exams/grading.py
  def grade_session(session: ExamSession) -> ExamAttempt
      # idempotent: session.attempt bor bo'lsa o'shani qaytaradi
  ```
  Endpointlar: `POST exams/start/`, `POST exams/{id}/answer/`, `POST exams/{id}/finish/`, `GET exams/{id}/`, `GET exams/`.

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_start_returns_mode_question_count_and_deadline(api, student, auth, questions_50):
    r = api.post("/api/v1/exams/start/", {"mode": 20}, format="json")
    b = r.json()
    assert len(b["questions"]) == 20 and b["pass_score"] == 18
    assert b["ends_at"]  # started_at + 25 daqiqa

def test_start_hides_correct_answer(api, student, auth, questions_50): ...

def test_answer_after_deadline_returns_409(api, student, auth, questions_50):
    ...  # ends_at ni o'tmishga surib qo'yish -> 409

def test_finish_grades_on_server(api, student, auth, questions_50):
    # mijoz "score" yuborsa ham e'tiborga olinmaydi
    ...

def test_finish_creates_exam_attempt(api, student, auth, questions_50):
    ...  # ExamAttempt.objects.count() == 1

# Review Focus #2
def test_finish_twice_is_idempotent(api, student, auth, questions_50):
    first = api.post(f"/api/v1/exams/{sid}/finish/").json()
    second = api.post(f"/api/v1/exams/{sid}/finish/")
    assert second.status_code == 409
    assert ExamAttempt.objects.count() == 1
    assert ExamSession.objects.get(pk=sid).score == first["score"]

def test_cannot_open_another_users_session(api, student, other_student, auth): ...  # 404

def test_deprecated_exam_generate_still_works(api, student, auth, questions_50):
    assert api.get("/api/v1/exam/generate/?count=20").status_code == 200
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_exams.py -v`
Expected: FAIL — `apps.exams` yo'q

- [ ] **Step 3: `apps/exams/` app'ini yaratish va modellar**

`INSTALLED_APPS` ga `"apps.exams"`. `start/` savollarni `visible_questions` dan `mode["questions"]` tasodifiy tanlaydi va `ExamSessionQuestion` qatorlarini yozadi.

- [ ] **Step 4: `grading.py` ni yozish**

`grade_session` — har bir `ExamSessionQuestion` uchun `is_correct` ni hisoblaydi, `session.score`, `finished_at` ni yozadi, `ExamAttempt` yaratadi va `session.attempt` ga bog'laydi. `session.attempt` allaqachon bor bo'lsa hech narsa o'zgartirmay o'shani qaytaradi. Hammasi bitta `transaction.atomic` ichida, `select_for_update` bilan.

- [ ] **Step 5: View va URL'lar**

`answer/` — `session.is_open` bo'lmasa `409`. `finish/` — `finished_at` bor bo'lsa `409`, aks holda `grade_session`. Barcha view'lar `queryset` ni `user=request.user` bilan cheklaydi.

- [ ] **Step 6: Deprecated belgilar**

`ExamGenerateView` va `ExamAttemptListCreateView` ga `@extend_schema(deprecated=True)`.

- [ ] **Step 7: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_exams.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/apps/exams backend/config backend/apps/content/views.py backend/tests/test_exams.py
git commit -m "feat: imtihon sessiyasi va server tomonda baholash"
```

---

### Task 12: BlitsResult

**Files:**
- Modify: `backend/apps/progress/{models,serializers,views,urls,admin}.py`
- Create: `backend/tests/test_blits_result.py`

**Interfaces:**
- Consumes: Task 7 (`Blits`)
- Produces:
  ```python
  # apps/progress/models.py
  class BlitsResult(models.Model):
      user, blits, score, total, created_at
  ```
  Endpoint: `GET/POST progress/blits-results/` — `TicketResult` bilan bir xil shakl (`{"blits": id, "items": [{"question": id, "answer": id|null}]}`).

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_blits_result_score_computed_on_server(api, student, auth, blits):
    r = api.post("/api/v1/progress/blits-results/",
                 {"blits": blits.id, "score": 999,
                  "items": [{"question": q1.id, "answer": correct.id},
                            {"question": q2.id, "answer": None}]}, format="json")
    assert r.json()["score"] == 1 and r.json()["total"] == 2

def test_blits_result_records_mistake(api, student, auth, blits):
    ...  # noto'g'ri javob Mistake.wrong_count ni oshiradi

def test_list_returns_only_own_results(api, student, other_student, auth): ...
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_blits_result.py -v`
Expected: FAIL — 404

- [ ] **Step 3: Model, serializer, view**

`TicketResultListCreateView` naqshini takrorlaydi: `QuestionAttempt` yozadi va `Mistake` hisoblagichini yangilaydi.

- [ ] **Step 4: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_blits_result.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/progress backend/tests/test_blits_result.py
git commit -m "feat: blits natijasi va xatolarga yozish"
```

---

### Task 13: `progress/services.py` va o'qituvchi API'si

**Files:**
- Create: `backend/apps/progress/services.py`, `backend/apps/accounts/teacher_views.py`, `backend/apps/accounts/teacher_urls.py`, `backend/tests/test_teacher_api.py`
- Modify: `backend/apps/progress/views.py` (`StatsView` — `user_stats` ga o'tadi), `backend/config/api_urls.py`

**Interfaces:**
- Consumes: Task 2 (`IsTeacherOrAdmin`), Task 11 (`ExamAttempt`), Task 12 (`BlitsResult`)
- Produces:
  ```python
  # apps/progress/services.py
  def user_stats(user) -> dict
      # {"lessons": {"done": int, "total": int},
      #  "tickets": {"done": int, "total": int, "best": int},
      #  "exams": {"attempts": int, "passed": int, "best": int},
      #  "mistakes": int}
  ```
  Endpointlar: `GET teacher/students/`, `GET teacher/students/{id}/stats/`, `GET teacher/stats/`.

`user_stats` `progress/stats/` va o'qituvchi endpointida bir xil ishlatiladi — statistika ikki joyda ikki xil hisoblanmaydi.

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_teacher_lists_only_own_branch_students(api, teacher, auth, branch_a, branch_b): ...

# Review Focus #3
def test_teacher_cannot_read_other_branch_student_stats(api, teacher, auth, other_branch_student):
    auth(api, teacher)
    assert api.get(f"/api/v1/teacher/students/{other_branch_student.id}/stats/").status_code == 404

def test_teacher_without_branch_sees_empty_list(api, teacher_no_branch, auth): ...

def test_admin_sees_all_branches(api, admin_user, auth): ...
def test_admin_can_filter_by_branch(api, admin_user, auth, branch_a): ...

def test_student_cannot_access_teacher_api(api, student, auth):
    auth(api, student); assert api.get("/api/v1/teacher/students/").status_code == 403

def test_own_stats_and_teacher_stats_agree(api, student, teacher, auth):
    # progress/stats/ va teacher/students/{id}/stats/ bir xil qiymat qaytaradi
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_teacher_api.py -v`
Expected: FAIL — 404

- [ ] **Step 3: `user_stats` ni yozish va `StatsView` ni unga o'tkazish**

Mavjud `StatsView` mantig'i `services.user_stats` ga ko'chadi; view faqat chaqiradi. Xulq o'zgarmaydi — mobil ilova shu javobni o'qiydi.

- [ ] **Step 4: O'qituvchi view'larini yozish**

Queryset: `User.objects.filter(role="student")`; `request.user.role == "teacher"` bo'lsa `branch=request.user.branch` bilan cheklanadi (`branch` `None` bo'lsa bo'sh queryset). `admin` uchun cheklov yo'q, `?branch=` bilan filtrlanadi. Cheklovdan tashqaridagi id → `404` (`403` emas — mavjudligini ham oshkor qilmaydi).

- [ ] **Step 5: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_teacher_api.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/progress backend/apps/accounts backend/config/api_urls.py backend/tests/test_teacher_api.py
git commit -m "feat: o'qituvchi uchun o'quvchilar natijasi API'si"
```

---

# FAZA 4 — Billing va migratsiya

### Task 14: billing app

**Files:**
- Create: `backend/apps/billing/` (`__init__.py`, `apps.py`, `models.py`, `serializers.py`, `views.py`, `urls.py`, `admin.py`, `migrations/`), `backend/apps/accounts/manage_views.py`, `backend/tests/test_billing.py`
- Modify: `backend/apps/accounts/models.py` (`branch`, `hujjat`), `backend/apps/content/manage_urls.py`, `backend/config/{settings,api_urls}.py`

**Interfaces:**
- Consumes: Task 2 (`IsAdminRole`), Task 9 (`manage/` prefiksi)
- Produces:
  ```python
  # apps/billing/models.py
  class Branch(models.Model): name, created_at, updated_at
  class StudentPayment(models.Model): user (OneToOne), amount, tolagani, created_at
      @property qoldiq(self) -> Decimal      # amount - tolagani
  class PaymentReport(models.Model): student_payment (FK), paid_amount, date, comment, created_at

  # apps/accounts/models.py
  User.branch: FK -> billing.Branch, null
  User.hujjat: str   # "+" | "-", default "-"

  # apps/accounts/manage_views.py
  class ManageUserViewSet(ModelViewSet)   # permission_classes = [IsAdminRole]
  ```
  Endpointlar: `manage/users/?role=&branch=&search=`, `manage/branches/`,
  `manage/payments/`, `manage/payment-reports/` — barchasi `IsAdminRole`.

`manage/users/` shefga o'quvchi yaratish (Task 4 dagi kirish kodini berishdan
oldingi qadam), rolini va filialini o'zgartirish imkonini beradi. Parol yozish
uchun `set_password` ishlatiladi va javobda hech qachon qaytmaydi.

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_payment_report_updates_tolagani(api, admin_user, auth, payment):
    api.post("/api/v1/manage/payment-reports/",
             {"student_payment": payment.id, "paid_amount": "50000"}, format="json")
    payment.refresh_from_db(); assert payment.tolagani == Decimal("50000")

def test_qoldiq_is_amount_minus_paid(payment): ...
def test_student_cannot_list_payments(api, student, auth): ...  # 403
def test_teacher_cannot_list_payments(api, teacher, auth): ...  # 403
def test_user_branch_is_nullable(student): assert student.branch is None

def test_admin_creates_student_with_hashed_password(api, admin_user, auth, branch_a):
    r = api.post("/api/v1/manage/users/",
                 {"phone": "901234567", "full_name": "Ali", "password": "1234",
                  "branch": branch_a.id}, format="json")
    assert r.status_code == 201
    assert r.json()["phone"] == "+998901234567"
    assert "password" not in r.json()
    assert User.objects.get(phone="+998901234567").check_password("1234")

def test_manage_users_filters_by_role_and_branch(api, admin_user, auth): ...
def test_teacher_cannot_create_user(api, teacher, auth): ...  # 403
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_billing.py -v`
Expected: FAIL — `apps.billing` yo'q

- [ ] **Step 3: App, modellar va migratsiyalar**

`User.branch` migratsiyasi `billing` dan keyin qo'llanishi uchun `dependencies` ga `billing.0001_initial` yoziladi.

- [ ] **Step 4: `PaymentReport` saqlanganda `tolagani` ni yangilash**

`post_save` signal emas — `PaymentReport.save()` ichida, `transaction.atomic` va `F()` ifodasi bilan (poyga holatidan saqlaydi).

- [ ] **Step 5: Serializer, viewset va Django admin**

- [ ] **Step 6: `ManageUserViewSet` ni yozish va `manage/` ga ulash**

`phone` `normalize_phone` dan o'tadi; `password` faqat yozish uchun (`write_only`) va `set_password` orqali saqlanadi. `?role=`, `?branch=`, `?search=` (ism va telefon bo'yicha) filtrlari.

- [ ] **Step 7: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_billing.py -v`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add backend/apps/billing backend/apps/accounts backend/apps/content/manage_urls.py backend/config backend/tests/test_billing.py
git commit -m "feat: filial, to'lov, to'lov hisoboti va foydalanuvchi boshqaruvi"
```

---

### Task 15: `import_content` buyrug'i

**Files:**
- Create: `backend/apps/content/management/commands/import_content.py`, `backend/tests/test_import_content.py`, `backend/tests/fixtures/admin_panel_db/*.json`

**Interfaces:**
- Consumes: Task 6 (`is_published`, `is_in_web`), Task 7 (`Blits`)
- Produces: `python manage.py import_content --path <dir> [--dry-run]`

Manba: `admin-panel/src/db/` — `sections.json`, `lessons.json`, `questions.json`, `answers.json`, `blits.json`. `variants.json` ixtiyoriy (hozir repoda yo'q) — bo'lsa `Ticket`/`TicketQuestion` ga yoziladi.

Moslashtirish **id bo'yicha**: `import_seoul` legacy PK'larni saqlagan, shuning uchun admin-panel id'lari baza id'lari bilan bir xil. `tartib` → `order`. Bazada bor-u JSON'da yo'q yozuv **o'chirilmaydi**, faqat hisobotda ko'rsatiladi.

- [ ] **Step 1: Kichik fixture tayyorlash**

`tests/fixtures/admin_panel_db/` — har bir fayldan 2–3 qator, haqiqiy shakl bilan (`{"id": 55, "lesson_id": 16, "question_uz": ..., "tartib": 1, "is_in_web": false}`).

- [ ] **Step 2: Failing testlarni yozish**

```python
def test_creates_missing_rows(db, fixture_dir):
    call_command("import_content", path=fixture_dir)
    assert Question.objects.filter(pk=55).exists()

def test_updates_existing_row_by_id(db, fixture_dir, question_55_with_old_text):
    call_command("import_content", path=fixture_dir)
    assert Question.objects.get(pk=55).text_uz == "..."  # fixture qiymati

def test_is_idempotent(db, fixture_dir):
    call_command("import_content", path=fixture_dir)
    counts = model_counts()
    call_command("import_content", path=fixture_dir)
    assert model_counts() == counts

def test_dry_run_writes_nothing(db, fixture_dir):
    call_command("import_content", path=fixture_dir, dry_run=True)
    assert Question.objects.count() == 0

def test_imported_questions_are_published(db, fixture_dir): ...

def test_row_missing_from_json_is_kept(db, fixture_dir, orphan_question):
    call_command("import_content", path=fixture_dir)
    assert Question.objects.filter(pk=orphan_question.pk).exists()

def test_tartib_maps_to_order(db, fixture_dir): ...
def test_blits_question_order_preserved(db, fixture_dir): ...
```

- [ ] **Step 3: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_import_content.py -v`
Expected: FAIL — buyruq yo'q

- [ ] **Step 4: Buyruqni yozish**

Tartib: sections → lessons → questions → answers → blits → variants. Hammasi bitta `transaction.atomic` ichida; `--dry-run` oxirida `transaction.set_rollback(True)`. Yakunda har bir model uchun `yaratildi / yangilandi / o'zgarmadi / JSON'da yo'q` hisoboti chiqadi.

- [ ] **Step 5: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_import_content.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps/content/management backend/tests
git commit -m "feat: admin-panel JSON'laridan kontent importi"
```

---

### Task 16: `import_web` buyrug'i

**Files:**
- Create: `backend/apps/billing/management/commands/import_web.py`, `backend/tests/test_import_web.py`

**Interfaces:**
- Consumes: Task 14 (`Branch`, `StudentPayment`, `PaymentReport`), Task 2 (`User.role`)
- Produces: `python manage.py import_web --database-url <eski web bazasi> [--dry-run]`

Ko'chadi: `home_branch` → `Branch`, `home_student` → `User` (`role="student"`), `home_studentpayment` → `StudentPayment`, `home_paymentreport` → `PaymentReport`. Telefon `901234567` → `+998901234567`.

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_student_becomes_user_with_normalized_phone(db, old_db):
    call_command("import_web", database_url=old_db)
    assert User.objects.filter(phone="+998901234567").exists()

def test_plaintext_password_is_hashed(db, old_db):
    call_command("import_web", database_url=old_db)
    u = User.objects.get(phone="+998901234567")
    assert u.password != "1234" and u.check_password("1234")

# Review Focus #5
def test_existing_user_is_not_overwritten(db, old_db, existing_user_same_phone):
    old_hash, old_name = existing_user_same_phone.password, existing_user_same_phone.full_name
    call_command("import_web", database_url=old_db)
    existing_user_same_phone.refresh_from_db()
    assert existing_user_same_phone.password == old_hash      # parol tegilmaydi
    assert existing_user_same_phone.full_name == old_name     # ism tegilmaydi
    assert existing_user_same_phone.branch is not None        # faqat bo'sh maydon to'ldiriladi

def test_existing_user_keeps_progress(db, old_db, existing_user_with_results): ...

def test_is_idempotent(db, old_db): ...
def test_invalid_phone_is_reported_not_raised(db, old_db_with_bad_phone):
    # noto'g'ri raqam butun importni to'xtatmaydi, hisobotga tushadi
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_import_web.py -v`
Expected: FAIL — buyruq yo'q

- [ ] **Step 3: Buyruqni yozish**

Eski bazaga `psycopg` bilan to'g'ridan-to'g'ri ulanadi (Django router emas — eski sxema boshqa loyihaniki).

**Mavjud foydalanuvchi qoidasi:** telefon bo'yicha `User` topilsa, **parol, ism va progress tegilmaydi**; faqat bo'sh maydonlar (`branch`, `hujjat`) to'ldiriladi va to'lov yozuvlari biriktiriladi. Yangi foydalanuvchi bo'lsa parol `set_password` orqali hash qilinadi.

Normalizatsiyadan o'tmagan raqam `ValidationError` ko'taradi — u tutiladi, qator o'tkazib yuboriladi va hisobotga yoziladi.

- [ ] **Step 4: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_import_web.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/apps/billing/management backend/tests/test_import_web.py
git commit -m "feat: eski web bazasidan foydalanuvchi va to'lov importi"
```

---

# FAZA 5 — Yakuniy

### Task 17: Django admin sozlash

**Files:**
- Modify: `backend/apps/*/admin.py`
- Create: `backend/apps/accounts/management/commands/setup_groups.py`, `backend/tests/test_admin.py`

**Interfaces:**
- Consumes: barcha modellar
- Produces: `python manage.py setup_groups` — `teacher` va `admin` guruhlarini kerakli permission'lar bilan yaratadi (idempotent).

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_every_model_is_registered_in_admin():
    from django.apps import apps as django_apps
    from django.contrib import admin
    missing = [m for m in django_apps.get_models()
               if m._meta.app_label.startswith(("accounts", "content", "exams",
                                                "progress", "billing", "notifications"))
               and m not in admin.site._registry]
    assert missing == []

def test_setup_groups_is_idempotent(db):
    call_command("setup_groups"); call_command("setup_groups")
    assert Group.objects.filter(name="teacher").count() == 1

def test_teacher_group_has_no_content_write_permission(db):
    call_command("setup_groups")
    perms = Group.objects.get(name="teacher").permissions.values_list("codename", flat=True)
    assert not any(p.startswith(("add_question", "change_question", "delete_question")) for p in perms)
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_admin.py -v`
Expected: FAIL

- [ ] **Step 3: Barcha modellarni admin'ga ro'yxatdan o'tkazish**

`Question` uchun `Answer` inline, `Ticket` uchun `TicketQuestion` inline, `Blits` uchun `BlitsQuestion` inline, `StudentPayment` uchun `PaymentReport` inline. `list_display`, `search_fields`, `list_filter` har biriga.

- [ ] **Step 4: `setup_groups` buyrug'ini yozish**

`teacher` — `progress` va `accounts` bo'yicha faqat `view_*`. `admin` — `content`, `billing`, `accounts` bo'yicha to'liq.

- [ ] **Step 5: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_admin.py -v`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add backend/apps backend/tests/test_admin.py
git commit -m "feat: Django admin va rol guruhlari"
```

---

### Task 18: `?compat=1` — eski nom taxalluslari

**Files:**
- Create: `backend/common/compat.py`, `backend/tests/test_compat.py`
- Modify: `backend/apps/content/serializers.py`

**Interfaces:**
- Consumes: Task 1 (`LangSerializerContextMixin`)
- Produces:
  ```python
  # common/compat.py
  def compat_requested(request) -> bool          # ?compat=1
  class CompatFieldsMixin:                        # serializer mixin
      compat_aliases: dict[str, str] = {}         # {"question_uz": "text_uz", ...}
      # to_representation compat so'ralgandagina taxalluslarni qo'shadi
  ```
  `QuestionSerializer`: `question_uz/ru/cry` → `text_uz/ru/cry`, `tartib` → `order`.
  `AnswerSerializer`: `answer_uz/ru/cry` → `text_uz/ru/cry`, `tartib` → `order`.

- [ ] **Step 1: Failing testlarni yozish**

```python
def test_aliases_absent_without_compat_flag(api, student, auth, question):
    body = api.get(f"/api/v1/questions/?lesson={question.lesson_id}").json()["results"][0]
    assert "question_uz" not in body

def test_aliases_present_with_compat_flag(api, student, auth, question):
    body = api.get(f"/api/v1/questions/?lesson={question.lesson_id}&compat=1").json()["results"][0]
    assert body["question_uz"] == question.text_uz
    assert body["tartib"] == question.order

def test_answer_aliases_present_with_compat_flag(api, student, auth, question): ...
def test_compat_does_not_reveal_is_true(api, student, auth, question): ...
```

- [ ] **Step 2: Testni ishga tushirish, yiqilishini tasdiqlash**

Run: `pytest tests/test_compat.py -v`
Expected: FAIL

- [ ] **Step 3: `CompatFieldsMixin` ni yozish va serializerlarga ulash**

- [ ] **Step 4: Testlar o'tishini tasdiqlash**

Run: `pytest tests/test_compat.py -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add backend/common/compat.py backend/apps/content/serializers.py backend/tests/test_compat.py
git commit -m "feat: eski frontlar uchun ?compat=1 maydon taxalluslari"
```

---

### Task 19: Deploy va hujjat

**Files:**
- Modify: `backend/docker-compose.yml`, `backend/Dockerfile`, `backend/config/urls.py`, `avtotest-online/README.md`
- Create: `backend/.env.example`

**Interfaces:**
- Consumes: barcha oldingi tasklar
- Produces: `docker compose up -d --build` bilan ko'tariladigan tizim; `/api/docs/` da to'liq Swagger.

- [ ] **Step 1: Failing testni yozish**

```python
def test_openapi_schema_builds_without_errors(api, admin_user, auth):
    r = api.get("/api/schema/")
    assert r.status_code == 200

def test_every_v1_url_appears_in_schema(api, admin_user, auth):
    # api_urls dagi har bir yo'l schema'da bor
```

- [ ] **Step 2: Testni ishga tushirish**

Run: `pytest tests/test_schema.py -v`
Expected: FAIL yoki drf-spectacular ogohlantirishlari

- [ ] **Step 3: Schema ogohlantirishlarini tuzatish**

`@extend_schema` bilan serializer'i noaniq view'larni belgilash.

- [ ] **Step 4: `docker-compose.yml`, `Dockerfile`, `.env.example`**

Postgres 15, gunicorn (3 worker), media volume, healthcheck. `.env.example` — `DATABASE_URL`, `SECRET_KEY`, `DEBUG`, `ALLOWED_HOSTS`, `CORS_ALLOWED_ORIGINS`, `APPLE_BUNDLE_ID`, `GOOGLE_CLIENT_IDS`, `TELEGRAM_BOT_TOKEN`.

- [ ] **Step 5: `README.md` ni yangilash**

Ishga tushirish, migratsiya tartibi (baza tiklash → `import_content` → `import_web` → media), endpoint jadvali, rollar.

- [ ] **Step 6: To'liq sinovni ishga tushirish**

Run: `pytest -v`
Expected: barcha testlar PASS

- [ ] **Step 7: Commit**

```bash
git add backend avtotest-online/README.md
git commit -m "feat: deploy sozlamalari va hujjat"
```

---

## Yakunda

Task 19 tugagach, spec'ning 14-bo'limiga ko'ra frontlarni ulash bo'yicha hisobot yoziladi: har bir front (mobil, web, admin-panel, darslik, imtihon, teacher) uchun qaysi endpointlarga ulanishi, qaysi maydonlar o'zgargani, `?compat=1` kerakmi, auth qanday o'tishi va qancha ish borligi.
