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

## Ishga tushirish

```bash
cd web/student            # yoki web/teacher
npm install
cp .env.example .env.local   # VITE_API_URL — backend manzili
npm run dev                  # http://localhost:5183
npm run build                # dist/ — statik fayllar
```

`npm run build` `.env.production` dagi API manzilini oladi
(`https://admin.avtotest-tayyorlov.uz/api/v1`).

## Serverga chiqarish

`dist/` — oddiy statik sayt (HashRouter, nisbiy yo'llar), istalgan manzilda
ochiladi. Masalan, tizim nginx'ida:

```nginx
server {
    server_name web.avtotest-tayyorlov.uz;
    root /var/www/avtotest-web;          # student/dist mazmuni
    index index.html;
    location / { try_files $uri $uri/ /index.html; }
    location /assets/ { expires 30d; add_header Cache-Control "public, immutable"; }
    # ... ssl (certbot)
}
```

Sayt backenddan **boshqa domenda** bo'lsa, `backend/.env` dagi
`CORS_ALLOWED_ORIGINS` ga uning manzilini qo'shing (vergul bilan), masalan
`https://web.avtotest-tayyorlov.uz,https://teacher.avtotest-tayyorlov.uz`,
so'ng `docker compose up -d`.

Server logida ichki yo'llar ko'rinadi (`docker compose logs -f backend`):

```
tunnel GET /questions/?compat=1&mode=study&page=2&page_size=200 -> 200 75ms
```
