# AvtoTest Online

AvtoTest loyihasi online rejimda ishlaydigan (Django + React + Electron) to'liq avtomatlashtirilgan o'quv va test platformasi.

## Loyiha Arxitekturasi
- **Backend:** Django, Django REST Framework, PostgreSQL. Docker yordamida izolyatsiya qilingan.
- **Frontend:** React (Vite).
- **Desktop Ilova:** Electron (Portable `.exe` dastur).

## Ishga Tushirish (Backend)

Backend to'liq Docker yordamida o'rnatiladi va ishga tushadi:

```bash
cd backend
docker-compose up --build -d
```
Backend 9005-portda ishlaydi: `http://localhost:9005`

### Ma'lumotlarni import qilish:
Eski JSON bazalarni PostgreSQL ga o'tkazish uchun:
```bash
docker-compose exec web python manage.py import_seoul
```
Admin yaratish:
```bash
docker-compose exec web python manage.py createsuperuser
```

## Ishga Tushirish (Frontend va Dastur)

Frontend kodlarini React serverida ishlatish uchun:
```bash
cd frontend
npm install
npm run dev
```

### Windows uchun tayyor `.exe` dastur yig'ish (Build):
Dastur `.exe` formatida ishlaydi va o'zining mustaqil brauzer oynasiga ega bo'ladi (Electron yordamida).

```bash
cd frontend
npm run build
npm run electron:packager
```
Yig'ilgan dastur `frontend/new_dist/AvtoQuiz-win32-x64` papkasida paydo bo'ladi.

## Asosiy o'zgarishlar va texnik xususiyatlar:
- Barcha statik .json fayllar PostgeSQL bazaga muvaffaqiyatli o'tkazildi va backend orqali optimallashtirildi.
- Token orqali himoya (Students modeli). Har bir so'rovda `?token=` ishlatiladi.
- Dastur dizayni moslashtirildi, `static-images` fayllar `public/` ichiga olindi.
- Electron dasturida `dist/` papkasidan barqaror ishlashi ta'minlandi, `npm run dev` bilan bog'liq eski kesh va xatolar tuzatildi.

---
**Muallif:** OQdevpy
