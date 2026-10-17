# Avto Teacher — o'qituvchi uchun darslik (desktop)

O'quvchi desktop ilovasi (`../frontend`) asosida: bir xil UI,
ma'lumot yagona backend API'sidan, kirish — shef bergan **kirish kodi** bilan
(kod bitta kompyuterga biriktiriladi).

Faqat **darslar** va **blits**: javoblar yopiq turadi, o'qituvchi javobni
bosganda to'g'risi yashil, noto'g'risi qizil bo'ladi. Test, imtihon va
variantlar yo'q.

```bash
cp .env.example .env.local   # VITE_API_URL ni to'ldiring (dev uchun)
npm install
npm run dev
npm run electron:build       # release/Avto Teacher Setup <versiya>.exe
```

Production build `.env.production` dagi API manzilini oladi.

Ilgari alohida `avtotest-desktop-teacher` reposida edi (shifrlangan `db.enc`,
eski server). Shu papkaga ko'chirilgach o'sha repo kerak emas; eski kodi
o'sha repoda `main`, qayta yig'ilgani `desktop-api` branch'ida qoldi.
