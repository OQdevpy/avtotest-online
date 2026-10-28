# Avtotest — web versiya

Desktop ilovalarning (`../frontend`, `../teacher`) brauzerda ochiladigan nusxasi:

| Papka | Nima | Dev port |
|---|---|---|
| `student/` | O'quvchi sayti (darslar, oraliq test, imtihon, variantlar) | 5183 |
| `teacher/` | O'qituvchi sayti — Avto Teacher (darslar, blits) | 5185 |

Kirish — shef bergan **kirish kodi** bilan (kod shu brauzerga biriktiriladi).
Desktop papkalari o'zgarmagan; Electron'ga xos qismlar (oynani yopish tugmasi,
`main.cjs`, installer) bu yerda yo'q.

## Backend bilan shifrlangan aloqa

Barcha API so'rovlari bitta shifrlangan konvert bo'lib `POST <API>/s/` ga
boradi (`src/api/secure.js`, backendda `common/tunnel.py`). Brauzerning Network
oynasida faqat shu ko'rinadi:

```
GET  /api/v1/s/key/   {"k": "..."}            ← serverning ochiq kaliti (sir emas)
POST /api/v1/s/       application/octet-stream ← o'qib bo'lmaydigan baytlar
```

Endpoint nomi, so'rov parametrlari, kirish kodi, token, savollar va to'g'ri
javoblar ko'rinmaydi; xato kodlari ham konvert ichida (tashqi status doim 200).

- Kalit: ECDH P-256 + HKDF-SHA256 → AES-256-GCM. Brauzer har sahifa
  yuklanganda yangi kalit juftligini yaratadi; maxfiy qismi eksport qilib
  bo'lmaydigan `CryptoKey` — boshqa odam Network yozuvidan ochib bo'lmaydi.
- Server kaliti `SECRET_KEY` dan hosil qilinadi — qo'shimcha sozlama yo'q.
- Kanal faqat web ilovalar ishlatadigan yo'llarni o'tkazadi (login-code, token
  yangilash, chiqish, kontent). Telefon+parol bilan kirish va `manage/` yopiq.
- WebCrypto faqat **HTTPS** (yoki `localhost`) da ishlaydi.

Cheklov: brauzer olgan ma'lumot baribir foydalanuvchining kompyuterida —
JavaScript debugger bilan sahifa xotirasini o'qish mumkin. Shifrlash Network
oynasidan va oraliq tarmoqdan himoya qiladi. Rasmlar (`/media/`) ochiq yuklanadi.

## Ishga tushirish (lokal)

```bash
cd web/student            # yoki web/teacher
npm install
cp .env.example .env.local   # VITE_API_URL — backend manzili
npm run dev                  # student: http://localhost:5183, teacher: :5185
```

## Serverga chiqarish

| Domen | Papka | Serverdagi joyi |
|---|---|---|
| `web.avtotest-tayyorlov.uz` | `web/student` | `/var/www/avtotest-web-student` |
| `teacher.avtotest-tayyorlov.uz` | `web/teacher` | `/var/www/avtotest-web-teacher` |

Brauzer faqat sayt domeniga murojaat qiladi: nginx `/api/v1/s/` ni backendga
(`127.0.0.1:8010`) uzatadi, `/media/` ni diskdan beradi, boshqa `/api/` yo'llari
`404`. Shuning uchun build'da API manzili nisbiy (`VITE_API_URL=/api/v1`,
`.env.production`) — backend domeni Network'da ham, kodda ham yo'q, CORS kerak emas.

### Birinchi marta (serverda)

1. **DNS:** `web` va `teacher` A-yozuvlari server IP'siga.
2. **Backend:** `backend/.env` dagi `ALLOWED_HOSTS` ga ikkala domenni qo'shing
   (nginx so'rovni shu `Host` bilan uzatadi), so'ng backendni yangilang:
   ```bash
   cd /root/avtotest/avtotest-online
   git pull
   # backend/.env: ALLOWED_HOSTS=...,web.avtotest-tayyorlov.uz,teacher.avtotest-tayyorlov.uz
   docker compose up -d --build
   ```
3. **Saytlar:** `./web/deploy.sh` (Node.js 18+ kerak) — ikkalasini yig'ib,
   `/var/www/avtotest-web-*` ga joylaydi.
4. **nginx + HTTPS** (HTTPS shart — WebCrypto oddiy HTTP'da ishlamaydi):
   ```bash
   cp web/nginx/web.avtotest-tayyorlov.uz.conf web/nginx/teacher.avtotest-tayyorlov.uz.conf /etc/nginx/sites-enabled/
   nginx -t && systemctl reload nginx
   certbot --nginx -d web.avtotest-tayyorlov.uz -d teacher.avtotest-tayyorlov.uz
   ```

### Keyingi yangilanishlar

```bash
cd /root/avtotest/avtotest-online && git pull
./web/deploy.sh               # yoki: ./web/deploy.sh student | teacher
docker compose up -d --build  # faqat backend o'zgargan bo'lsa
```

Server logida ichki yo'llar ko'rinadi (`docker compose logs -f backend`):

```
tunnel GET /questions/?compat=1&mode=study&page=2&page_size=200 -> 200 75ms
```
