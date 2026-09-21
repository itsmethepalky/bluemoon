# The Blue Moon — API Documentation

## Overview

The backend is implemented using FastAPI.

The frontend communicates with the backend for application operations while Supabase Auth handles login and registration.

The exact route list is defined in:

```text
backend/app/routers/
```

## Authentication

Protected API requests use:

```http
Authorization: Bearer <SUPABASE_ACCESS_TOKEN>
```

The backend validates the authenticated user before processing protected operations.

## Main API domains

The application backend is organized into routers for business resources such as:

- Products
- Sales
- Purchases
- Suppliers
- Customers
- Users
- Reports
- Inventory-related operations

The exact paths and request/response schemas should be treated as the source of truth in:

```text
backend/app/routers/
backend/app/schemas.py
```

## Roles

Protected endpoints may require:

- Authenticated user
- Staff user
- Administrator

The backend should always be treated as the authorization boundary.

## Error handling

API clients should handle normal HTTP error responses rather than assuming every request succeeds.

When debugging, inspect the FastAPI server logs and the HTTP response body.

## Extending the API

When adding a new resource:

1. Create/update SQLAlchemy models.
2. Add Pydantic schemas.
3. Add a router.
4. Add authentication/authorization dependencies.
5. Validate inputs.
6. Add database operations.
7. Register the router in the application.
8. Connect the frontend.
9. Test normal and unauthorized requests.
10. Document the change.
