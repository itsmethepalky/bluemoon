# The Blue Moon — Deployment Guide

## Production architecture

```text
Browser
   |
   v
FastAPI application
   |
   +---- Supabase Auth
   |
   +---- Supabase PostgreSQL
```

The frontend is served by FastAPI.

## Render deployment

Create a Python web service and connect the repository.

### Build command

A typical build command is:

```bash
pip install -r backend/requirements.txt
```

### Start command

Run from the repository root:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

If the deployment configuration uses `backend` as its working directory, use:

```bash
uvicorn app.main:app --host 0.0.0.0 --port $PORT
```

Use the command that matches the selected service root.

## Environment variables

Configure production values in the hosting provider:

```env
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
DATABASE_URL=
```

Never commit production secrets.

## Database connection

The backend can use the Supabase Transaction Pooler. The SQLAlchemy URL should use the PostgreSQL driver format:

```text
postgresql+psycopg2://...
```

Make sure the connection settings match the pooler configuration provided by Supabase.

## Production checklist

- [ ] Production Supabase project configured
- [ ] Database migrations applied
- [ ] Environment variables configured
- [ ] Service-role key kept server-side
- [ ] Debug/reload disabled
- [ ] HTTPS enabled by hosting provider
- [ ] CORS configured for the actual deployment
- [ ] Admin account secured
- [ ] Demo/seed credentials removed or changed
- [ ] Application tested after deployment
- [ ] Database backups/retention configured according to business needs

## Important

The free tier of some hosting providers may suspend or sleep inactive services. This is a hosting-provider behavior, not an application requirement. Choose a suitable production plan if continuous availability is required.
