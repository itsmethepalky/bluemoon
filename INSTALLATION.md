# The Blue Moon — Installation Guide

## Requirements

- Python 3.11–3.13
- Git
- A Supabase project
- Internet access for installing Python dependencies and connecting to Supabase

## 1. Get the project

```bash
git clone <repository-url>
cd the-blue-moon
```

## 2. Create the Supabase project

Create a PostgreSQL project in Supabase.

The application uses:

- Supabase Auth
- Supabase PostgreSQL
- Row Level Security (RLS)
- Transaction Pooler for the backend database connection

Apply the SQL files in `database/migrations/` in their documented order.

## 3. Configure backend environment

```bash
cd backend
cp .env.example .env
```

Fill in the required values:

```env
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
DATABASE_URL=postgresql+psycopg2://...
```

Never commit `.env`.

The `service_role` key is server-only and must never be placed in frontend JavaScript.

## 4. Install dependencies

Recommended:

```bash
python -m venv .venv
```

Activate the environment and install:

```bash
pip install -r requirements.txt
```

On restricted environments where appropriate:

```bash
pip install -r requirements.txt --break-system-packages
```

## 5. Seed development data

From `backend/`:

```bash
python seed.py
```

The seed script creates demo authentication users and sample business data.

Do not use seed/demo credentials as production credentials.

## 6. Start the application

```bash
uvicorn app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/
```

The FastAPI application serves the frontend, so a separate frontend server is normally unnecessary.

## 7. Verify the installation

Test:

1. Registration
2. Login
3. Dashboard access
4. Product creation/editing
5. Stock changes
6. POS sale
7. Purchase
8. Customer creation
9. Credit/payment
10. Return
11. Reports
12. Staff/admin permissions

If all core flows work, the installation is ready for use.
