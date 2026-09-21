# The Blue Moon — Database Documentation

## Database platform

The application uses PostgreSQL hosted by Supabase.

Supabase additionally provides:

- Authentication
- Row Level Security
- Database management
- API/database tooling

## Schema

The database is organized around the application's main business domains:

```text
Authentication / Profiles
        |
        +---- Customers
        |
        +---- Staff/Admin roles

Products
   |
   +---- Categories
   +---- Brands
   |
   +---- Inventory operations

Suppliers
   |
   +---- Purchases
          |
          +---- Purchase Items

Customers
   |
   +---- Sales
          |
          +---- Sale Items
          +---- Payments
          +---- Returns
```

The exact schema is defined by the SQL files in:

```text
database/migrations/
```

Apply migrations in their intended order.

## Migrations

Migrations should be treated as the source of truth for reproducing the database schema.

Do not manually change production tables without documenting the change in a migration.

## Authentication/profile relationship

Supabase Auth owns authentication identities.

The application's profile layer stores application-specific user information such as role.

A database trigger creates the corresponding profile when a new authentication user is registered.

## Roles

The application uses role information stored in the application's profile data.

Typical roles:

- `admin`
- `staff`
- `customer`

Backend authorization uses these roles to control access.

## Inventory

Inventory changes occur as part of business operations such as:

- Purchases
- Sales
- Returns

Business logic should be used instead of manually editing stock values.

## Data integrity

Foreign keys and database constraints should be preserved when modifying the schema.

If a buyer changes the schema, they should create a migration documenting the change.
