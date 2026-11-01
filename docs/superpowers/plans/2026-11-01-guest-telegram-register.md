# Mehmon rejimi va Telegram orqali ro'yxatdan o'tish — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Yangi foydalanuvchi mobil ilovani 5 kun mehmon sifatida ishlatadi, so'ng Telegram bot orqali bitta havola va bitta tugma bilan raqamini tasdiqlab ro'yxatdan o'tadi. Shunda mehmon hisobi o'quvchiga aylanadi.

**Architecture:** Mehmon — `role="guest"` bo'lgan `User` va 5 kunlik `Device` sessiyasi, tokenida `did` bor; muddat har so'rovda tekshiriladi. Telegram tasdiqlash sessiyasi Redis'da turadi (token → phone/purpose/status). Bot `/start <token>` va kontakt orqali sessiyani `verified`/`mismatch` qiladi, ilova holatni polling bilan so'raydi. `register/` tasdiqlangan tokenni va mehmonning refresh tokenini qabul qiladi.

**Tech Stack:** Django 6, DRF, SimpleJWT, Redis, python-telegram-bot 21; Expo 57 / React Native 0.86 / TypeScript.

**Spec:** `docs/superpowers/specs/2026-11-01-telegram-registration-design.md`

## Global Constraints

- Ikki repo: backend — `C:\Users\o.qosimov\projects\myself\avtotest-online` (branch `feat/guest-telegram-register` from `master`); mobil — `C:\Users\o.qosimov\projects\myself\avtotest\avtotest-mobile` (branch `feat/guest-telegram-register` from `main`). Mobil repodagi kuzatilmagan `*.csv` fayllarga tegilmaydi.
- `settings.GUEST_DAYS = 5`; verification sessiya umri 600 s, tasdiqlangandan keyin yana 600 s.
- `settings.REGISTER_REQUIRE_TELEGRAM = env_bool("REGISTER_REQUIRE_TELEGRAM", True)`.
- Eski ilovaga xato javobi aynan: `{"code": "update_required", "detail": "Ilovaning yangi versiyasini o'rnating."}` (status 400).
- Mehmon muddati tugaganda: status 401, body `{"detail": "Sinov muddati tugadi. Ro'yxatdan o'ting.", "code": "guest_expired"}`.
- Bot havolasi: `https://t.me/{telegram.BOT_USERNAME}?start=<token>`; token faqat `[A-Za-z0-9_-]`, ≤ 64 belgi.
- Kod izohlari, xabarlar va commit matnlari o'zbekcha, mavjud uslubda (`backend: …`, `mobil: …`). Commit oxirida `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Backend testlari: `backend/` ichida `<venv>/Scripts/python.exe -m pytest -q -p no:cacheprovider` (venv: sessiya scratchpad'idagi `venv`, `requirements.txt` o'rnatilgan). Baseline: 391 passed, 3 skipped.
- Mobil tekshiruv: `npx tsc --noEmit` (mobil repo ildizida) xatosiz.
- Bot faqat mavjud `TELEGRAM_BOT_TOKEN` bilan ishlaydi; lokal tekshiruvda bot o'rniga sessiya shell orqali `verified` qilinadi.

## Review Focus

- Muddati tugagan mehmon 5 kundan keyin ro'yxatdan o'tadi (access token allaqachon eskirgan) → natijalari saqlangan holda o'quvchiga aylanadi (Task 4: `test_expired_guest_converts_with_refresh`).
- Talaba (`Student` yozuvi bor) parolni tiklaydi → yangi parol bilan kiradi, eski PIN ishlamaydi, `User.password` bo'sh satrga aylanmaydi (Task 4: `test_student_reset_switches_to_own_password`).
- Telegram'dagi raqam formati boshqacha (`998901234567`, `+998 90 123 45 67`) lekin aynan shu raqam → `verified`; xorijiy raqam → `foreign` (Task 3: `test_resolve_contact_normalizes`, `test_resolve_contact_foreign`).
- Bir sessiya tokeni bilan ikki marta ro'yxatdan o'tishga urinish → ikkinchisi rad etiladi (Task 4: `test_verification_token_single_use`).
- Hisobidan chiqqan o'quvchi ilovani qayta ochadi → login ekrani, yangi mehmon emas (Task 7, qo'lda/Playwright tekshiruvi).

---

### Task 1: Mehmon roli, `POST /auth/guest/` va sessiya muddati

**Files:**
- Modify: `backend/apps/accounts/models.py` (Role.GUEST, `guest_phone()`), `backend/apps/accounts/devices.py`, `backend/apps/accounts/serializers.py` (`issue_tokens`), `backend/apps/accounts/views.py` (`GuestView`, `ChangePasswordView`), `backend/apps/accounts/urls.py`, `backend/apps/accounts/admin.py`, `backend/apps/accounts/management/commands/prune_devices.py`, `backend/common/authentication.py`, `backend/common/permissions.py`, `backend/config/settings.py`, `nginx/conf.d/default.conf`, `docs/DEPLOY.md`
- Create: `backend/apps/accounts/migrations/0007_user_role_guest.py` (`makemigrations` bilan), `backend/tests/test_guest.py`

**Interfaces:**
- Produces: `User.Role.GUEST == "guest"`; `User.is_guest -> bool` (property); `guest_phone() -> str` (13 belgi, `"g"` + 12 hex, `+998` bilan boshlanmaydi, noyob); `devices.register_guest_device(user, refresh, label: str, machine_id: str) -> Device` (`platform="mobile"`, `expires_at = now + GUEST_DAYS`); `issue_tokens(..., guest: bool = False)` — `guest=True` bo'lsa `register_guest_device` va `did` claim; `common.permissions.IsRegistered` (mehmon emas); URL nomi `guest` → `/api/v1/auth/guest/`.

- [ ] **Step 1: Branch**

`git switch -c feat/guest-telegram-register` (avtotest-online, `master` dan).

- [ ] **Step 2: Failing testlar — `backend/tests/test_guest.py`**

```python
GUEST_URL = "/api/v1/auth/guest/"

def test_guest_creates_session(api, db):
    r = api.post(GUEST_URL, {"device_id": "a" * 32, "lang": "uz"}, format="json")
    assert r.status_code == 201
    assert r.data["user"]["role"] == "guest"
    assert r.data["tokens"]["access"] and r.data["guest_until"]
    user = User.objects.get(pk=r.data["user"]["id"])
    assert not user.phone.startswith("+998") and len(user.phone) <= 13
    device = user.devices.get()
    assert device.platform == "mobile" and device.machine_id == "a" * 32
    assert (device.expires_at - device.created_at).days == 5  # GUEST_DAYS

def test_guest_reads_content(api, db, ticket):  # 200 on /api/v1/tickets/
def test_guest_is_not_pro(api, db):  # user.pro_active is False in /auth/me/
def test_expired_guest_gets_guest_expired(api, db):
    # guest yaratiladi, Device.expires_at o'tmishga suriladi
    # GET /api/v1/tickets/ → 401, r.data["code"] == "guest_expired"
def test_closed_code_session_still_session_closed(...)  # mavjud kirish kodi xatti-harakati o'zgarmaydi: is_active=False → 401, code "session_closed"
def test_guest_cannot_change_password(api, db):  # POST /auth/change-password/ → 403
def test_guest_throttled(api, db, settings):  # rate "guest" 2/hour bilan uchinchisi 429
def test_prune_deletes_old_guests(db):
    # date_joined = now - 36 kun bo'lgan guest o'chadi; now - 10 kun bo'lgani qoladi; student tegilmaydi
```

- [ ] **Step 3: Testlar yiqiladi**

Run: `python -m pytest tests/test_guest.py -q` → FAIL (404 / `guest` yo'q).

- [ ] **Step 4: Model va migratsiya**

`Role.GUEST = "guest", "Mehmon"`; `is_guest` property; `guest_phone()` `secrets.token_hex(6)` bilan, band bo'lsa qayta. `python manage.py makemigrations accounts -n user_role_guest`.

- [ ] **Step 5: Sessiya va token**

`register_guest_device` — `devices.py` da; limit tekshirilmaydi. `issue_tokens(guest=True)` — `did` claim har doim qo'yiladi (hozir faqat `machine_id` bo'lsa qo'yiladi; mehmonda `machine_id` = `device_id`).

- [ ] **Step 6: Muddat tekshiruvi — `common/authentication.py`**

`SessionAwareJWTAuthentication.get_user`: `did` bor tokenda `Device` topilmasa yoki `is_active=False` → hozirgidek `session_closed`. `device.is_expired` va `user.is_guest` → `AuthenticationFailed({"detail": "Sinov muddati tugadi. Ro'yxatdan o'ting.", "code": "guest_expired"})` (dict — DRF `code` ni javobga chiqarishi uchun). Mehmon bo'lmagan va muddati o'tgan → `session_closed`.

- [ ] **Step 7: `GuestView` va ruxsatlar**

`GuestView(generics.GenericAPIView)`: `AllowAny`, `throttle_classes=[ScopedRateThrottle]`, `throttle_scope="guest"`. Serializer maydonlari: `device_id` (CharField ≤64, majburiy), `lang` (User.Language choice, default `uz`), `device_label` (ixtiyoriy). Javob 201: `{user, tokens, guest_until}` (`guest_until` = device.expires_at ISO). Settings: `REST_FRAMEWORK["DEFAULT_THROTTLE_RATES"] = {"guest": "20/hour"}`, `GUEST_DAYS = 5`. `ChangePasswordView.permission_classes = [IsAuthenticated, IsRegistered]`.

- [ ] **Step 8: Admin, prune, nginx, DEPLOY**

- **Admin** (`admin.py`, foydalanuvchilar ro'yxati): `guest_until` ustuni — faol mehmon qurilmasining `expires_at`, mehmon bo'lmasa `—`.
- **`prune_devices`**: qo'shimcha ravishda `role="guest"` va `date_joined < now - (GUEST_DAYS + 30) kun` bo'lgan userlarni o'chiradi, sonini chiqaradi.
- **nginx** (`nginx/conf.d/default.conf`): `location = /api/v1/auth/guest/` bloki `login_limit` zonasi bilan (login bloki nusxasi).
- **`docs/DEPLOY.md`**: yangi bo'lim "Mehmon rejimi" — tizim nginx'iga ham shu cheklovni qo'shish, `prune_devices` mehmonlarni tozalashi.

- [ ] **Step 9: Testlar o'tadi va to'liq to'plam**

Run: `python -m pytest -q -p no:cacheprovider` → hammasi PASS (391 + yangi).

- [ ] **Step 10: Commit** — `backend: mehmon rejimi — POST /auth/guest/, 5 kunlik sessiya`

---

### Task 2: Telegram tasdiqlash sessiyasi va `telegram/start|status`

**Files:**
- Create: `backend/apps/telegramauth/verification.py`, `backend/tests/test_telegram_verification.py`
- Modify: `backend/apps/telegramauth/views.py`, `backend/apps/telegramauth/serializers.py`, `backend/apps/telegramauth/urls.py`, `backend/requirements.txt` (`fakeredis==2.26.2`), `backend/tests/conftest.py`

**Interfaces:**
- Consumes: `otpstore.client()`; `accounts.models.normalize_phone`, `User`.
- Produces (`verification.py`):
  - `SESSION_TTL = 600`; `class Status: PENDING="pending"; VERIFIED="verified"; MISMATCH="mismatch"; EXPIRED="expired"`
  - `start_session(phone: str, purpose: str, lang: str) -> str` (token, `secrets.token_urlsafe(24)`); bir telefonga 10 daqiqada 5 tadan ortiq → `TooManySessions` istisnosi
  - `get_session(token: str) -> dict | None` — `{"phone", "purpose", "lang", "status", "telegram_id"}`
  - `status_of(token: str) -> str` (yo'q bo'lsa `expired`)
  - `mark(token: str, status: str, telegram_id: int | None = None) -> None` — `verified` bo'lsa TTL yana 600 s
  - `consume(token: str, phone: str, purpose: str) -> bool` — faqat `verified` va mos bo'lsa, o'chiradi
  - `bind_chat(telegram_id: int, token: str) -> None`; `chat_token(telegram_id: int) -> str | None` (TTL = SESSION_TTL)
  - `bot_link(token: str) -> str`
  - Redis kalitlari: `tgv:{token}`, `tgv:chat:{telegram_id}`, `tgv:count:{phone}`
- conftest fixture: `fake_redis` (autouse emas) — `otpstore._client` ni `fakeredis.FakeRedis(decode_responses=True)` bilan almashtiradi.

- [ ] **Step 1: Failing testlar**

```python
START = "/api/v1/auth/telegram/start/"

def test_start_returns_link(api, db, fake_redis):
    r = api.post(START, {"phone": "901234567", "purpose": "register", "lang": "uz"}, format="json")
    assert r.status_code == 200
    assert r.data["link"] == f"https://t.me/AvtotestTayyorlovBot?start={r.data['token']}"
    assert re.fullmatch(r"[A-Za-z0-9_-]{1,64}", r.data["token"]) and r.data["expires_in"] == 600

def test_status_flow(api, db, fake_redis):  # pending → mark(verified) → "verified"; noma'lum token → "expired"
def test_register_phone_taken(api, student, fake_redis):  # student.phone bilan → 400, code "phone_taken"
def test_guest_phone_not_taken(...)  # mehmon bor bo'lsa ham +998 raqam bo'sh hisoblanadi
def test_reset_no_user(api, db, fake_redis):  # → 404, code "no_user"
def test_too_many_sessions(api, db, fake_redis):  # 6-urinish → 429, code "too_many"
def test_consume_only_verified(db, fake_redis):  # pending → False; verified → True; ikkinchi marta → False; boshqa phone → False
```

- [ ] **Step 2: Yiqilishini tekshirish** — `python -m pytest tests/test_telegram_verification.py -q` → FAIL.

- [ ] **Step 3: `verification.py`** — yuqoridagi interfeys, `otpstore` uslubida JSON qiymatlar.

- [ ] **Step 4: View'lar**

`TelegramStartView` (`AllowAny`, `{phone: PhoneField, purpose: register|reset, lang: optional}`) → `{token, link, expires_in}`; xatolar `_error(code, detail, status)` orqali (`phone_taken` 400, `no_user` 404, `too_many` 429). `TelegramStatusView` GET `telegram/status/<str:token>/` → `{status}`. URL'lar `apps/telegramauth/urls.py` ga (`auth/` ostida).

- [ ] **Step 5: Testlar o'tadi va to'liq to'plam** → PASS.

- [ ] **Step 6: Commit** — `backend: Telegram tasdiqlash sessiyasi — auth/telegram/start va status`

---

### Task 3: Bot — `/start <token>` va kontaktni solishtirish

**Files:**
- Modify: `backend/apps/telegramauth/verification.py` (`resolve_contact`, `mask_phone`), `backend/apps/telegramauth/telegram.py` (TEXTS), `backend/apps/telegramauth/management/commands/runbot.py`
- Test: `backend/tests/test_telegram_verification.py`

**Interfaces:**
- Consumes: Task 2 `get_session`, `mark`, `chat_token`, `bind_chat`, `Status`.
- Produces:
  - `mask_phone(phone: str) -> str` — `"+998901234567"` → `"+998 90 ***-45-67"`
  - `resolve_contact(token: str, shared_raw: str, telegram_id: int) -> tuple[str, str | None, str | None]` → `(outcome, session_phone, shared_phone)`; outcome: `"verified"` | `"mismatch"` | `"foreign"` (normallashmaydigan / `+998` emas) | `"expired"`. `verified` va `mismatch` sessiyani `mark` qiladi; `foreign` → `mismatch` deb belgilanadi.
  - TEXTS kalitlari (uz/kr/ru): `verify_prompt`, `link_expired`, `verified`, `mismatch` (`{shared}`, `{entered}`), `foreign_number`.

- [ ] **Step 1: Failing testlar**

```python
def test_mask_phone():
    assert mask_phone("+998901234567") == "+998 90 ***-45-67"

def test_resolve_contact_match(db, fake_redis):  # outcome "verified", status_of == "verified", telegram_id yozilgan
def test_resolve_contact_normalizes(db, fake_redis):
    for raw in ("998901234567", "+998 90 123 45 67"):  # sessiya +998901234567
        assert resolve_contact(new_token(), raw, 7)[0] == "verified"
def test_resolve_contact_mismatch(db, fake_redis):  # ("mismatch", "+998901234567", "+998911112233"), status "mismatch"
def test_resolve_contact_foreign(db, fake_redis):  # "+79161234567" → outcome "foreign"
def test_resolve_contact_expired(db, fake_redis):  # noma'lum token → ("expired", None, None)
```

- [ ] **Step 2: Yiqilishini tekshirish** → FAIL.

- [ ] **Step 3: `mask_phone`, `resolve_contact`, TEXTS**

Matnlar mazmuni spec'dagidek:
- `verified`: "✅ Raqamingiz tasdiqlandi. Ilovaga qayting."
- `mismatch`: "❌ Siz ulashgan raqam ({shared}) ilovaga kiritilgan raqam ({entered}) bilan mos emas. Ilovaga qaytib, Telegram'dagi raqamingizni kiriting."
- `foreign_number`: "Faqat O'zbekiston raqami bilan ro'yxatdan o'tish mumkin."

`kr` matnlari `uz` ning kirillchasi, `ru` tarjima.

- [ ] **Step 4: `runbot.py`**

- **`start`:** `context.args` bo'sh bo'lsa hozirgi oqim. Aks holda `get_session(args[0])`:
  - yo'q bo'lsa → `link_expired`;
  - bor bo'lsa → `bind_chat`, `lang = tg.app_lang_to_bot(session["lang"])`, `verify_prompt` + `_contact_keyboard(lang)`.
- **`on_contact`:** mavjud o'z-kontakt tekshiruvidan keyin `chat_token(from_user.id)` bor bo'lsa `resolve_contact` (sync_to_async):
  - `verified` → `link_contact(...)` + `verified` matni + `ReplyKeyboardRemove()`;
  - `mismatch` → `mismatch` matni (ikkala raqam `mask_phone` bilan) + `ReplyKeyboardRemove()`;
  - `foreign` → `foreign_number`;
  - `expired` → `link_expired`.

  Token yo'q bo'lsa hozirgi oqim.

- [ ] **Step 5: Testlar o'tadi, to'liq to'plam PASS; `python -c "import apps.telegramauth.management.commands.runbot"` (DJANGO_SETTINGS_MODULE bilan) xatosiz import bo'ladi.**

- [ ] **Step 6: Commit** — `backend: bot — havola orqali bitta tugma bilan raqamni tasdiqlash`

---

### Task 4: Ro'yxatdan o'tish, mehmonni aylantirish, parol tiklash

**Files:**
- Modify: `backend/apps/accounts/serializers.py` (`RegisterSerializer`, `LoginSerializer`), `backend/apps/accounts/views.py` (`RegisterView`), `backend/apps/telegramauth/views.py` (`SendCodeView`, `ResetPasswordView`), `backend/config/settings.py`, `README.md` (Autentifikatsiya bo'limi)
- Test: `backend/tests/test_register_telegram.py`; mavjud registratsiya testlari yangi talabga moslanadi (`REGISTER_REQUIRE_TELEGRAM=False` fixture yoki `verification` bilan)

**Interfaces:**
- Consumes: Task 2 `verification.consume`; Task 1 `User.is_guest`.
- Produces: `POST /auth/register/` body: `{phone, password, full_name?, language?, verification?, guest_refresh?}`; `POST /auth/reset-password/` `{phone, token, password}` — `token` Telegram verification tokeni yoki eski OTP tokeni.

- [ ] **Step 1: Failing testlar**

```python
def test_register_requires_verification(api, db):  # verification'siz → 400, data == {"code": "update_required", "detail": "Ilovaning yangi versiyasini o'rnating."}
def test_register_with_verified_token(api, db, fake_redis):  # 201, user.role == "student", is_pro True (12 kun sovg'a)
def test_register_wrong_phone_token(api, db, fake_redis):  # boshqa raqam uchun tasdiqlangan token → 400, code "verification_invalid"
def test_verification_token_single_use(api, db, fake_redis):  # ikkinchi register → 400
def test_guest_converts_keeps_progress(api, db, fake_redis, question):
    # guest yaratiladi, SavedQuestion qo'shiladi; register(guest_refresh=...) → o'sha user.pk, role "student", SavedQuestion saqlangan, eski guest Device is_active False
def test_expired_guest_converts_with_refresh(api, db, fake_redis):  # guest Device.expires_at o'tmishda, access ham eskirgan → baribir aylanadi
def test_guest_refresh_of_student_ignored(api, student, fake_redis):  # student refresh berilsa yangi hisob ochiladi, student tegilmaydi
def test_flag_off_allows_old_register(api, db, settings):  # REGISTER_REQUIRE_TELEGRAM=False → verification'siz 201
def test_send_code_register_update_required(api, db, settings):  # purpose=register → 400 update_required; purpose=reset o'zgarmaydi
def test_reset_with_telegram_token(api, student, fake_redis):  # verified reset token → 204, yangi parol bilan login 200
def test_student_reset_switches_to_own_password(api, db, fake_redis):
    # Student(phone, password="1234") → reset "yangi123" → login "yangi123" 200, login "1234" 400,
    # Student.password == "", user.has_usable_password() and user.password != ""
```

- [ ] **Step 2: Yiqilishini tekshirish** → FAIL.

- [ ] **Step 3: Register**

`RegisterSerializer`: `verification` va `guest_refresh` (CharField, ixtiyoriy, write_only).
- **`validate`:** `REGISTER_REQUIRE_TELEGRAM` va `verification` yo'q bo'lsa → `ValidationError` aynan `update_required` dict bilan. Javob tanasi `{"code","detail"}` bo'lishi uchun view `serializers.ValidationError` ni ushlab `Response(..., 400)` qaytaradi. `verification` bor bo'lsa `verification.consume(token, phone, "register")`, False → `verification_invalid`.
- **Mehmonni topish:** `guest_refresh` → `RefreshToken(raw)` (TokenError bo'lsa e'tiborsiz). User `role=guest` va `is_active` bo'lsa o'sha userga phone, password, full_name, language, `role=student` yoziladi, 12 kun PRO beriladi (mavjud qoida), uning barcha `Device` lari `is_active=False`. Aks holda hozirgidek yangi user.
- **Tokenlar:** `auth_response` odatdagi mobil tokenlarni chiqaradi.

- [ ] **Step 4: send-code va reset**

- **`SendCodeView`:** `purpose == "register"` va `REGISTER_REQUIRE_TELEGRAM` → `_error("update_required", "Ilovaning yangi versiyasini o'rnating.")`.
- **`ResetPasswordView`:** avval `verification.consume(token, phone, "reset")`, bo'lmasa `otpstore.consume_token(...)`. Parol o'rnatilgach `Student.objects.filter(user=user).update(password="")` — `update()`, `save()` emas, aks holda signal `User` parolini bo'sh satrga almashtiradi.
- **`LoginSerializer`:** `student.password` bo'sh bo'lsa `authenticate(...)` yo'liga tushadi.

- [ ] **Step 5: README** — Autentifikatsiya jadvaliga `auth/guest/`, `auth/telegram/start/`, `auth/telegram/status/<token>/`; registratsiya `verification` talabi va `REGISTER_REQUIRE_TELEGRAM`.

- [ ] **Step 6: To'liq to'plam PASS.**

- [ ] **Step 7: Commit** — `backend: ro'yxatdan o'tish Telegram tasdig'i bilan, mehmon o'quvchiga aylanadi, talaba paroli tiklanadi`

---

### Task 5: Mobil — API qatlami va qurilma belgisi

**Files:**
- Create: `avtotest-mobile/src/api/telegram.ts`, `avtotest-mobile/src/install.ts`
- Modify: `avtotest-mobile/src/api/index.ts`, `avtotest-mobile/src/api/client.ts`, `avtotest-mobile/src/api/types.ts`

**Interfaces:**
- Produces:
  - `types.ts`: `ApiUser.role: 'guest' | 'student' | 'teacher' | 'admin'`; `GuestResponse = AuthResponse & { guest_until: string }`
  - `install.ts`: `getInstall(): Promise<{ deviceId: string; hadSession: boolean }>` (AsyncStorage `yolchi.install.v1`, `deviceId` — 32 hex), `markHadSession(): Promise<void>`
  - `api/index.ts`: `guest(deviceId: string, lang: string): Promise<GuestResponse>` (tokenlarni saqlaydi); `register(phone, password, fullName, language, verification: string, guestRefresh?: string)`
  - `api/telegram.ts`: `type VerifyStatus = 'pending' | 'verified' | 'mismatch' | 'expired'`; `startVerification(phone: string, purpose: 'register' | 'reset', lang: string): Promise<{ token: string; link: string; expiresIn: number }>`; `verificationStatus(token: string): Promise<VerifyStatus>`; `class VerifyError extends Error { code: 'phone_taken' | 'no_user' | 'too_many' }`
  - `client.ts`: `setGuestExpiredHandler(fn: (() => void) | null)`; `getRefreshToken(): string | null`. 401 javobida `data.code === 'guest_expired'` bo'lsa refresh qilinmaydi, tokenlar o'chirilmaydi, `onUnauthorized` emas, guest-expired handler chaqiriladi.

- [ ] **Step 1: Branch** — mobil repoda `git switch -c feat/guest-telegram-register`.
- [ ] **Step 2: Fayllar** — yuqoridagi interfeyslar; `client.ts` da 401 tanasi refresh'dan oldin o'qiladi (`res.clone().json()` xavfsiz parse).
- [ ] **Step 3: `npx tsc --noEmit`** → xatosiz (eski `register` chaqiruvi Task 7 da almashguncha `verification` ni vaqtincha ixtiyoriy qilish mumkin — Task 7 da majburiy bo'ladi).
- [ ] **Step 4: Commit** — `mobil: mehmon va Telegram tasdiqlash API'lari`

---

### Task 6: Mobil — mehmon rejimi (ishga tushish, banner, profil, muddat tugashi)

**Files:**
- Create: `avtotest-mobile/src/screens/GuestExpired.tsx`
- Modify: `avtotest-mobile/src/store.tsx`, `avtotest-mobile/src/AppShell.tsx` (`SCREENS.guestExpired`), `avtotest-mobile/src/screens/Home.tsx` (`GuestBanner`), `avtotest-mobile/src/screens/Profile.tsx`, `avtotest-mobile/src/screens/Login.tsx` (`initialView` prop), `avtotest-mobile/src/i18n/translations.ts` (`Strings`, `uz`, `ru`)

**Interfaces:**
- Consumes: Task 5 `guest`, `getInstall`, `markHadSession`, `setGuestExpiredHandler`.
- Produces (store): `Screen` ga `'guestExpired'`; `isGuest: boolean` (`s.user?.role === 'guest'`); `guestDaysLeft: number | null`; `openAuth(view: 'register' | 'login'): void` (login ekraniga kerakli ko'rinishda o'tadi, mehmon tokenlari saqlanadi).
- Tarjima kalitlari: `guest_banner` ("Mehmon rejimi · {n} kun qoldi"), `guest_register`, `guest_login`, `guest_expired_title` ("Sinov muddati tugadi"), `guest_expired_sub` ("Davom etish uchun ro'yxatdan o'ting"), `guest_start_failed`.

- [ ] **Step 1: Ishga tushish mantig'i (`store.tsx` hydrate)**

- Token bor → `me()`:
  - muvaffaqiyat → `markHadSession()`, `home`;
  - `guest_expired` → `guestExpired`.
- Token yo'q, `!hadSession` → `api.guest(deviceId, lang)` → `markHadSession()` → `home`. Tarmoq xatosi bo'lsa `login` ekrani `guest_start_failed` xabari bilan.
- Token yo'q, `hadSession` → `login`.
- `logout` → `login` (mehmon yaratilmaydi). `setGuestExpiredHandler` → `{screen: 'guestExpired', hist: []}`.

- [ ] **Step 2: UI**

- **`GuestBanner`:** Home'da `ProBanner` o'rnida, faqat `isGuest` bo'lsa. Matn + "Ro'yxatdan o'tish" (`openAuth('register')`) + "Kirish" (`openAuth('login')`).
- **Profile:** mehmon uchun shu ikki tugma; parol, o'chirish va chiqish bandlari yashiriladi.
- **`GuestExpired`:** sarlavha, izoh va o'sha ikki tugma; orqaga yo'l yo'q (`hist: []`, Android back hech narsa qilmaydi).

- [ ] **Step 3: `npx tsc --noEmit`** → xatosiz.
- [ ] **Step 4: Commit** — `mobil: mehmon rejimi — ro'yxatdan o'tmasdan 5 kun`

---

### Task 7: Mobil — Telegram qadami (Register va Forgot)

**Files:**
- Create: `avtotest-mobile/src/screens/auth/TelegramStep.tsx`
- Modify: `avtotest-mobile/src/screens/auth/Register.tsx`, `avtotest-mobile/src/screens/auth/Forgot.tsx`, `avtotest-mobile/src/store.tsx` (`register` imzosi), `avtotest-mobile/src/i18n/translations.ts`
- Delete: `avtotest-mobile/src/screens/auth/OtpStep.tsx`, `avtotest-mobile/src/api/otp.ts` dagi `sendCode`/`verifyCode` (foydalanilmay qolsa; `normalizePhone` va `resetPassword` qoladi)

**Interfaces:**
- Consumes: Task 5 `startVerification`, `verificationStatus`, `getRefreshToken`; Task 6 `openAuth`.
- Produces: `<TelegramStep phone={string} purpose={'register' | 'reset'} onVerified={(token: string) => Promise<void>} onChangePhone={() => void} />`; store `register(phone, password, fullName, verification: string)` — mehmon bo'lsa `guestRefresh = getRefreshToken()` yuboriladi.
- Tarjima kalitlari: `tg_title`, `tg_sub`, `tg_open` ("Telegram'da tasdiqlash"), `tg_waiting` ("Telegram'da «Kontaktni ulashish»ni bosing…"), `tg_mismatch` ("Telegram'dagi raqamingiz boshqa. Raqamni o'zgartiring"), `tg_expired` ("Vaqt tugadi"), `tg_retry`, `tg_change_phone`, `tg_reopen` ("Havolani qayta ochish"), `err_phone_taken`, `err_no_user`, `err_too_many`.

- [ ] **Step 1: `TelegramStep`**

- **Ochilganda:** `startVerification` → `Linking.openURL(link)`.
- **Polling:** har 2000 ms `verificationStatus`; `AppState` `active` bo'lganda darhol; ekran yopilganda to'xtaydi.
- **Holatlar:**
  - `verified` → `onVerified(token)` (bir marta);
  - `mismatch` → `tg_mismatch` + "Raqamni o'zgartirish";
  - `expired` → `tg_expired` + "Qaytadan" (yangi sessiya).
- **Tugmalar:** "Havolani qayta ochish" va "Raqamni o'zgartirish" doim ko'rinadi.
- **`VerifyError` kodlari** → mos `err_*` matni, `onChangePhone` bilan formaga qaytish.

- [ ] **Step 2: Register** — qadamlar `'form' | 'telegram'`, `LangStep` olib tashlanadi, `AuthShell` `hideLang` olib tashlanadi; `StepBar total={2}`; `onVerified` → `register(phone, pass, name, token)`.

- [ ] **Step 3: Forgot** — qadamlar `'phone' | 'telegram' | 'pass'`; `pass` qadamida `resetPassword(phone, token, pass)`; bot havolasi/`notLinked` qismi olib tashlanadi.

- [ ] **Step 4: `npx tsc --noEmit`** → xatosiz.

- [ ] **Step 5: Commit** — `mobil: ro'yxatdan o'tish va parol tiklash — Telegram'da bitta tugma`

---

### Task 8: Lokal uchidan-uchigacha tekshiruv

**Files:**
- Create (scratchpad, repo emas): Playwright skripti `scratchpad/pw/guest_flow.cjs`

- [ ] **Step 1:** Backendni qayta yig'ish: `docker compose up -d --build backend` (avtotest-online); `docker compose exec backend python manage.py migrate` muvaffaqiyatli.
- [ ] **Step 2:** Expo web'ni qayta ishga tushirish (`EXPO_PUBLIC_API_URL=http://localhost:9005`, port 8090), brauzer xotirasi toza.
- [ ] **Step 3 — Playwright, mehmon:** birinchi ochilishda login emas, Home + "Mehmon rejimi · 5 kun qoldi" banneri chiqadi. Biletlar ochiladi, Mavzular qulf bilan turadi.
- [ ] **Step 4 — Playwright, ro'yxatdan o'tish:**
  - "Ro'yxatdan o'tish" → forma → Telegram qadami.
  - Bot o'rniga shell: `verification.mark(token, "verified", 1)`. Tokenni `tgv:*` kalitidan oling.
  - Ilova o'zi Home'ga o'tadi, banner yo'qoladi; backend'da shu user `role=student`, `pk` o'zgarmagan.
- [ ] **Step 5 — muddat tugashi:**
  - Yangi brauzer konteksti → mehmon.
  - Shell: guest `Device.expires_at` o'tmishga suriladi.
  - Sahifa yangilanadi → "Sinov muddati tugadi" ekrani chiqadi. Yangilash yana shu ekranni beradi.
- [ ] **Step 6 — chiqish:** ro'yxatdan o'tgan user Profil → Chiqish → login ekrani. Sahifa yangilansa ham login, mehmon yaratilmaydi.
- [ ] **Step 7:** Skrinshotlarni ko'rib chiqish va natijani hisobotda yozish. Commit yo'q.
