# Makhzan Desktop Wrapper

يحوي هذا المجلّد مجموعة أدوات لتشغيل واجهة الـ Flask داخل تطبيق سطح مكتب بسيط باستخدام Electron.

## المتطلبات

- Node.js (النسخة 18 أو أحدث)
- Python 3 مع المتطلبات الحالية (`requirements.txt`)

## تشغيل النسخة المحلية

```bash
cd desktop
npm install
npm run start
```

سيقوم الأمر `npm run start` بتشغيل Flask (`py -3 ../Makhzan/app.py`) وتشغيل Electron بعد التأكد من أن `http://localhost:5000` متاح.

## الحزم والـ Build

- يمكنك إنتاج حزمة مستعملة `electron-builder` أو `electron-packager` إذا حبيت تصدر التطبيق لويندوز/ماك/لينكس، بس ده خارج نطاق هذه الإضافة.

