# The Blue Moon — Troubleshooting

## Application does not start

Run:

```bash
uvicorn app.main:app --reload
```

Check the terminal for the first traceback/error.

Common causes:

- Missing dependency
- Incorrect working directory
- Invalid environment variable
- Python version mismatch
- Database connection failure

## Database connection error

Check:

- `DATABASE_URL`
- Database password
- Supabase project reference
- Pooler hostname and port
- PostgreSQL driver prefix

Expected SQLAlchemy format:

```text
postgresql+psycopg2://...
```

Do not paste database passwords into public issues or repositories.

## Login works but API requests fail

Check:

- The browser has a valid Supabase session.
- The access token is being sent as a Bearer token.
- The backend can validate the token.
- The user's `profiles` row exists.
- The user's role is correct.

## Registration does not create a profile

Check the Supabase database trigger and the migration responsible for the new-user profile creation.

Confirm that the required migration was applied successfully.

## Permission denied

Check the user's role.

Typical role hierarchy:

```text
customer
staff
admin
```

Admin-only operations require an administrator role.

## Products do not update stock

Check the corresponding sale/purchase operation and database records.

Verify that:

- The product exists.
- The quantity is valid.
- The transaction completed successfully.
- The correct product ID was sent.

## Frontend cannot reach backend

If running locally, verify:

```text
http://127.0.0.1:8000/
```

The frontend is designed to communicate with the backend served by the same application.

## Render deployment fails

Check:

1. Build command.
2. Start command.
3. Python version.
4. Environment variables.
5. Working directory.
6. Supabase connection.
7. Application logs.

A typical root-directory start command is:

```bash
uvicorn backend.app.main:app --host 0.0.0.0 --port $PORT
```

## Service appears to sleep

Some hosting free tiers suspend inactive services. This is controlled by the hosting provider.

Use a plan with continuous service availability if the business requires it.

## Security test reports a finding

First determine whether the finding is:

- Application code
- Dependency
- Hosting configuration
- Supabase configuration
- Rate limiting
- Scanner false positive

Do not disable a security control simply to make a scanner report disappear. Verify the underlying issue first.
