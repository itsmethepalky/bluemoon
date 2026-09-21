# The Blue Moon — Security

## Security architecture

The application uses multiple security layers:

```text
Supabase Auth
     ↓
Access token
     ↓
FastAPI token validation
     ↓
Role verification
     ↓
Protected business operation
     ↓
PostgreSQL
```

Supabase Row Level Security is also enabled as a defense-in-depth measure.

## Secrets

Never commit:

- Database passwords
- Supabase service-role keys
- Production API secrets
- Private credentials

Use environment variables instead.

The service-role key bypasses RLS and must remain on the backend.

## Authentication

Login and registration are handled through Supabase Auth.

Protected API requests use the authenticated Supabase access token.

## Authorization

Authorization is enforced on the backend through role-aware dependencies.

Frontend UI restrictions should not be considered the security boundary.

## Database security

RLS is enabled on application tables as an additional protection layer.

The backend has controlled access to the database for business operations.

## Security testing

The current project has been tested after implementation, including online security checking.

The reported overall security assessment was **A+** at the time of testing.

Security testing is not a permanent guarantee. Dependencies, hosting configuration, database configuration and application code should be reviewed periodically.

## Reporting a vulnerability

If you discover a security vulnerability:

1. Do not publish sensitive details publicly.
2. Do not include credentials in an issue.
3. Contact the software owner privately.
4. Provide enough information to reproduce the issue safely.
5. Allow reasonable time for investigation and remediation.

## Buyer responsibility

A buyer who modifies or deploys the application is responsible for securing their own production environment, credentials, hosting configuration, third-party services and custom modifications.

The commercial license does not guarantee that every buyer deployment will remain secure after modification.
