# Makhzan

A private warehouse/inventory management project prepared for documenting stock, operations, and admin workflows.

## Status

Private pinned candidate. Review the implementation, screenshots, and secrets before making this repository public.

## Project Goals

- Organize warehouse or inventory workflows
- Present stock and operational data clearly
- Support admin-style management screens
- Prepare the project for portfolio and company review

## Expected Features

- Inventory or warehouse item management
- Dashboard-style overview screens
- Search, filtering, and operational workflows
- Backend or data-source integration where configured
- Role or admin workflow documentation when available

## Getting Started

Clone the repository:

```bash
git clone https://github.com/yousefm2311/Makhzan.git
cd Makhzan
```

Install and run using the project stack found in the repository:

```bash
flutter pub get
flutter run
```

or, for a web/backend stack:

```bash
npm install
npm run dev
```

## Environment Variables

Create local configuration only when external services are required.

```env
API_BASE_URL=
DATABASE_URL=
AUTH_SECRET=
```

Never commit production credentials, database dumps, private customer data, or API keys.

## Screenshots

Add dashboard, inventory list, item details, and workflow screenshots before pinning publicly.

```md
![Makhzan dashboard](docs/screenshots/dashboard.png)
```

## Roadmap

- Document exact app architecture
- Add screenshots and demo flow
- Add setup notes for the real stack
- Add test/build commands

## Author

Yousef Mohamed

- GitHub: https://github.com/yousefm2311
mac
cd Makhzan
python3 -m venv .venv
source .venv/bin/activate
pip install Flask Flask-SQLAlchemy Flask-Login Flask-Migrate Flask-WTF email-validator openpyxl
cd Makhzan
python app.py


windows
cd Makhzan
python -m venv .venv
.venv\Scripts\activate
pip install Flask Flask-SQLAlchemy Flask-Login Flask-Migrate Flask-WTF email-validator openpyxl
cd Makhzan
python app.py

