<div align="center">
  <!-- مسار لوجو المشروع لو موجود -->
  <img src="Makhzan/static/images/logo.png" alt="Makhzan Logo" width="120" onerror="this.style.display='none'" />

  # Makhzan - نظام المخازن المتكامل (Warehouse Management System)

  **نظام متكامل واحترافي لإدارة المخازن، المبيعات، المشتريات، العهد، والفروع مع دعم كامل لنظام الصلاحيات المعقد، التوقيع الإلكتروني، والتقارير المتقدمة.**

  <!-- شارات التقنيات -->
  [![Flask](https://img.shields.io/badge/Flask-000000?style=for-the-badge&logo=flask&logoColor=white)](https://flask.palletsprojects.com/)
  [![SQLite](https://img.shields.io/badge/SQLite-07405E?style=for-the-badge&logo=sqlite&logoColor=white)](https://sqlite.org/)
  [![Bootstrap](https://img.shields.io/badge/Bootstrap-563D7C?style=for-the-badge&logo=bootstrap&logoColor=white)](https://getbootstrap.com/)
  [![Electron](https://img.shields.io/badge/Electron-47848F?style=for-the-badge&logo=electron&logoColor=white)](https://www.electronjs.org/)
</div>

---

## 📖 نظرة عامة (Overview)

**Makhzan (مخزن)** هو تطبيق ويب وتطبيق سطح مكتب مخصص لإدارة المخازن بشكل احترافي للشركات والمحلات. يحل النظام مشكلة التشتت في متابعة المخزون، حيث يوفر دورة مستندية كاملة تبدأ من استلام البضائع من الموردين، وتوزيعها على الفروع أو مواقع التخزين، وصرف العهد للموظفين باستردادها أو تسجيل التوالف (الهالك). كما يتيح عمليات البيع (POS) وإصدار الفواتير للعملاء. 

النظام يدعم **التوقيع الإلكتروني** للموافقات، و**سجل التدقيق (Audit Trail)** لتتبع كل حركة يقوم بها أي مستخدم لضمان أعلى معايير الأمان والشفافية.

---

## ✨ المميزات الأساسية (Key Features)

*   **📦 إدارة المخزون المتقدمة:** تتبع حركات المخزون، جرد المخازن (Stocktakes)، وتوزيع المنتجات على مواقع تخزين مختلفة داخل الفروع.
*   **👥 إدارة الفروع والعهد (Employees & Branches):** ربط الموظفين بالفروع، طلبات صرف العهد (Issue Requests) مع دورة موافقات (Approval Workflow) وتوقيع إلكتروني، وتسجيل مرتجعات العهد.
*   **🛒 المشتريات والمبيعات:** فواتير شراء من الموردين ومبيعات للعملاء (نقدي/آجل)، مع تتبع الدفعات المستحقة (Due Payments).
*   **🔐 نظام صلاحيات دقيق جداً (RBAC):** أدوار مخصصة (Admin, Warehouse Manager, Approver, Auditor, Cashier) مع إمكانية تخصيص الصلاحيات لكل مستخدم على مستوى الشاشة (Granular Permissions).
*   **📑 تقارير متكاملة وتصدير (PDF & Excel):** دعم كامل للغة العربية في تصدير الـ PDF (عبر ReportLab و Arabic Reshaper)، وتصدير بيانات المخزون والحركات إلى Excel (عبر OpenPyXL).
*   **🛡️ سجل التدقيق (Audit Logs):** تسجيل كل نقرة وتعديل داخل النظام (من قام بالتعديل، متى، وما هو التعديل) لمنع التلاعب.
*   **💻 تطبيق سطح مكتب (Desktop App):** النظام يحتوي على نسخة Electron لتغليف الـ Flask App ليعمل كتطبيق سطح مكتب (Desktop App) بسهولة دون الحاجة لفتح المتصفح.

---

## 🏗 التقنيات المستخدمة وهيكلة المشروع (Tech Stack & Architecture)

يعتمد المشروع على بنية متينة وسريعة مناسبة للاستخدام المحلي أو الاستضافة السحابية:

*   **الواجهة الخلفية (Backend):** Python / Flask
*   **قاعدة البيانات (Database):** SQLite (عبر SQLAlchemy ORM)
*   **الواجهة الأمامية (Frontend):** HTML5, CSS3, Bootstrap 5, JavaScript, Jinja2 Templates (دعم الوضع الليلي Dark Mode)
*   **تغليف سطح المكتب (Desktop Wrapper):** Electron.js, Node.js
*   **التقارير (Reports):** ReportLab (PDF), OpenPyXL (Excel)
*   **إدارة الحالة والجلسات:** Flask-Login
*   **إدارة النماذج والتحقق:** Flask-WTF

### 📂 هيكلة المشروع (Directory Structure)

```text
Makhzan/
├── Makhzan/                  # مجلد تطبيق الويب (Flask App)
│   ├── app.py                # نقطة الدخول (Entry point) وإعدادات Flask الأساسية
│   ├── models.py             # هيكل قاعدة البيانات والجداول (SQLAlchemy Models)
│   ├── routes.py             # مسارات الويب (Controllers / Views)
│   ├── forms.py              # النماذج والتحقق من صحة الإدخالات (WTForms)
│   ├── static/               # ملفات الـ CSS, JS, الصور والخطوط
│   └── templates/            # ملفات الـ HTML (Jinja2) مقسمة حسب الوحدات (فواتير، مخزون، تقارير...)
├── desktop/                  # مجلد تطبيق سطح المكتب (Electron Wrapper)
│   ├── main.js               # الكود الأساسي لتشغيل نافذة Electron وتشغيل سيرفر Flask
│   ├── preload.js            # جسر التواصل بين الـ Node.js والـ Frontend
│   └── package.json          # إعدادات الـ Node واعتمادات Electron
├── migrations/               # ملفات تهجير قاعدة البيانات (Flask-Migrate / Alembic)
├── requirements.txt          # مكتبات بايثون المطلوبة لتشغيل المشروع
└── README.md                 # هذا الملف
```

---

## 🚀 دليل التشغيل (Getting Started)

### 📋 المتطلبات الأساسية (Prerequisites)
*   تثبيت **Python** (إصدار 3.8 أو أحدث)
*   تثبيت **Node.js** (إذا كنت ترغب في تشغيل نسخة سطح المكتب Electron)

### 🛠️ خطوات التثبيت والتشغيل (Web Version)

1. **نسخ المشروع:**
   افتح الـ Terminal (أو موجه الأوامر) واذهب لمجلد المشروع.

2. **إنشاء البيئة الوهمية (Virtual Environment) وتفعيلها:**
   ```bash
   python -m venv venv
   # في الويندوز:
   venv\Scripts\activate
   # في الماك/لينكس:
   source venv/bin/activate
   ```

3. **تثبيت المكتبات المطلوبة:**
   ```bash
   pip install -r requirements.txt
   ```

4. **تشغيل المشروع:**
   ```bash
   cd Makhzan
   flask run --host=0.0.0.0 --port=5000
   ```
   *سيقوم النظام تلقائياً بإنشاء قاعدة البيانات (`makhzan.db`) وإنشاء مستخدم افتراضي بصلاحيات Admin (اسم المستخدم: admin, كلمة المرور: admin123).*

5. افتح المتصفح على الرابط: `http://localhost:5000`

---

### 🖥️ خطوات تشغيل تطبيق سطح المكتب (Desktop Electron App)

إذا أردت تشغيل المشروع كتطبيق مستقل يشبه البرامج العادية:

1. تأكد أنك قمت بتثبيت مكتبات الـ Python (الخطوات 1 إلى 3 في الأعلى).
2. افتح نافذة Terminal جديدة وادخل إلى مجلد `desktop`:
   ```bash
   cd desktop
   ```
3. تثبيت حزم النود:
   ```bash
   npm install
   ```
4. تشغيل البرنامج:
   ```bash
   npm start
   ```
   *هذا الأمر سيقوم بتشغيل سيرفر الـ Flask في الخلفية (عبر Python) ثم فتح نافذة Electron تعرض النظام.*

---

## 💡 نصائح الاستخدام

- **الوضع الافتراضي (الشركة مقابل التجزئة):** يحتوي النظام على حماية للمسارات (Routes). إذا كان النظام موجهًا كمخزن لشركة، يمكن للمسؤول إخفاء واجهات البيع (POS) من الإعدادات، والتركيز على العهد وجرد المخازن.
- **التوقيع الإلكتروني:** في طلبات صرف العهد (Issue Requests) سيُطلب من المدير الموافقة وإدخال كلمة المرور الخاصة به كتوقيع إلكتروني موثق يظهر في الـ PDF.
- **تخصيص الصلاحيات:** لا تعطِ صلاحية `admin` إلا لمدير النظام. يمكنك إنشاء دور `warehouse_manager` وتحديد الشاشات التي يراها من قائمة تعديل المستخدم.

---

## 📄 الترخيص (License)
هذا المشروع ملكية خاصة وتم تطويره كحل متكامل لإدارة المخازن. جميع الحقوق محفوظة لمالك الكود الأصلي.
