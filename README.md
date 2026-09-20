# The Blue Moon — Small Business Management & POS System

A small-business management and point-of-sale system: product/inventory
management, purchases & suppliers, customers & store credit, POS billing
with returns, and sales/inventory/profit reports.

## Stack

- **Database + Auth: Supabase** (hosted Postgres, Row Level Security, and
  Supabase Auth for login/sign-up). The underlying project is still called
  **"BookBridge POS"** in your Supabase dashboard (`ap-south-1`) — that's
  just its internal project name and isn't shown anywhere in the app;
  rename it from *Project Settings → General* if you'd like the dashboard
  to say "The Blue Moon" too.
- **Backend: FastAPI** (Python) — business logic (stock updates, invoice
  numbering, credit balances, reports) sitting on top of the Supabase
  Postgres database, connecting with the direct Postgres connection.
- **Frontend: HTML / CSS / vanilla JS**, using `supabase-js` (via CDN)
  directly for login/sign-up, and calling the FastAPI backend for
  everything else. Charts via Chart.js.

```
Browser ──(login/signup)──> Supabase Auth
Browser ──(everything else)──> FastAPI backend ──> Supabase Postgres
```

## Project layout

```
backend/            FastAPI app
  app/
    main.py         App entrypoint, CORS, serves frontend/ as static files
    config.py       Reads backend/.env
    database.py     SQLAlchemy engine (points at Supabase Postgres)
    supabase_client.py   Supabase Python clients (anon + service role)
    security.py     Validates Supabase access tokens
    deps.py         FastAPI auth dependencies (get_current_user, require_*)
    models.py       SQLAlchemy models (mirrors the Supabase schema exactly)
    schemas.py      Pydantic request/response schemas
    routers/        One file per resource (products, sales, purchases, ...)
  seed.py           Creates demo logins + sample catalog data
  requirements.txt
  .env.example      Copy to .env and fill in the blanks (see below)
frontend/           Static HTML/CSS/JS, served by the backend at "/"
database/
  migrations/       The exact SQL already applied to the Supabase project,
                     in order — for your documentation/ERD, and to reproduce
                     the schema on a fresh Supabase project if you ever need to
```

## One-time setup

### 1. Get your Supabase secrets

Two values in `backend/.env` are **secrets** that can't be handed to you
programmatically — grab them from the
[Supabase dashboard](https://supabase.com/dashboard/project/fulnozrxrucvmvhwfipe):

1. **Database password / connection string** — *Project Settings → Database
   → Connection string → URI tab*. Pick **"Transaction pooler"**. If you
   don't remember the database password, reset it from the same page.
2. **`service_role` key** — *Project Settings → API*. Click "reveal" next
   to the `service_role` key. This key bypasses Row Level Security and can
   manage every login — never expose it to the frontend or commit it.

### 2. Configure the backend

```bash
cd backend
cp .env.example .env
```

Open `.env` and paste in the two secrets above. `SUPABASE_URL` and
`SUPABASE_ANON_KEY` are already filled in (they're public values — the
frontend embeds the same anon key directly in `frontend/js/api.js`).

For `DATABASE_URL`, take the connection string from step 1 and change its
prefix from `postgresql://` to `postgresql+psycopg2://`, e.g.:

```
DATABASE_URL=postgresql+psycopg2://postgres.fulnozrxrucvmvhwfipe:YOUR-PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres
```

### 3. Install & seed

```bash
pip install -r requirements.txt --break-system-packages   # drop the flag if you're using a venv
python seed.py
```

`seed.py` creates three demo logins (via the Supabase Admin API — real
Supabase Auth users) plus sample categories/brands/products/suppliers.
Safe to re-run.

### 4. Run it

```bash
uvicorn app.main:app --reload
```

Open **http://127.0.0.1:8000/** — the backend also serves the frontend, so
there's nothing else to start.

## How auth works

- Login and sign-up happen **entirely client-side** via `supabase-js`
  (`frontend/js/api.js`, `login.html`, `register.html`) — the backend has
  no `/login` or `/register` endpoint.
- The moment someone signs up, a Postgres trigger
  (`private.handle_new_auth_user`, see
  `database/migrations/002_signup_trigger_and_role_helpers.sql`)
  automatically creates their `profiles` row (and a `customers` row, for
  shoppers).
- Every other request carries the Supabase access token as a Bearer
  token; FastAPI validates it against Supabase (`app/security.py`) and
  looks up the caller's role from `profiles` (the single source of truth —
  an admin changing someone's role in the Staff Accounts page updates this
  table directly).
- Row Level Security is enabled on every table as defense-in-depth. The
  backend connects with a direct Postgres connection (which bypasses RLS,
  like any direct Postgres superuser connection would) and enforces
  permissions itself via `deps.require_staff` / `require_admin`; RLS is
  what protects the data if anything ever queries Supabase directly.

## Feature checklist (mapped to the project proposal)

- **User & role management** — admin/staff/customer roles, staff accounts
  managed under *Staff Accounts* (admin-only)
- **Product & inventory CRUD** — categories, brands, products, soft
  delete (`is_active`), low-stock flag via `reorder_level`
- **Sales & POS** — cart-based billing, discounts/tax, cash/card/mobile/
  credit payment, auto stock deduction, returns
- **Purchases & suppliers** — supplier CRUD, multi-item purchases that
  automatically increase stock
- **Customers & credit** — credit limit/balance, payment recording,
  purchase history (also visible to the customer themselves via *My
  Account*)
- **Reports & dashboard** — today/month sales, low-stock list, sales
  trend, top products, inventory value by category, profit estimate

## A note on testing

This was built in a sandboxed environment with **no internet access**, so
I could not `pip install` FastAPI/SQLAlchemy/`supabase-py` or actually
boot the server to test it end-to-end. Everything was written carefully
and cross-checked by hand (types, column names, request/response shapes
between every router and its frontend caller), and the SQL migrations
*were* applied to and verified against a real, live Supabase project. But
please test thoroughly once you run it locally — in particular:

- The exact response shape of `supabase-py`'s `auth.admin.create_user` /
  `update_user_by_id` calls in `backend/app/routers/users.py` and
  `backend/seed.py` (I used broad exception handling there specifically
  because I couldn't verify the exact error types against a live install).
- End-to-end sign-up → profile-creation-trigger → login flow.
