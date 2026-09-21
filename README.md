🌙 The Blue Moon — Small Business Management & POS System

The Blue Moon is a full-stack small-business management and point-of-sale (POS) system designed for shops and small retail businesses.

It provides product and inventory management, purchasing, supplier management, customer accounts, store credit, POS billing, returns, and business reports through a responsive web interface.

The system uses Supabase for authentication and PostgreSQL, FastAPI for the backend business logic, and a lightweight HTML/CSS/JavaScript frontend.

---

✨ Features

👤 User & Role Management

- Supabase Authentication
- User registration and login
- Role-based access control
- "admin", "staff", and "customer" roles
- Admin-only staff account management
- Customer self-service account
- Protected backend API endpoints
- Supabase Row Level Security (RLS)

📦 Products & Inventory

- Product CRUD
- Categories
- Brands
- SKU/product codes
- Selling and purchase prices
- Current stock tracking
- Reorder levels
- Low-stock detection
- Product activation/deactivation
- Automatic inventory updates

🛒 POS & Sales

- Cart-based POS interface
- Multiple products per invoice
- Discounts
- Tax support
- Cash payments
- Card payments
- Mobile payments
- Credit sales
- Automatic stock deduction
- Invoice generation/numbering
- Sales history
- Sales returns

🚚 Purchases & Suppliers

- Supplier management
- Purchase records
- Multi-item purchases
- Automatic stock increases
- Purchase history
- Supplier information management

👥 Customers & Store Credit

- Customer management
- Credit limits
- Outstanding credit balances
- Credit payment recording
- Customer purchase history
- Customer account dashboard
- Customer access to their own account information

📊 Dashboard & Reports

- Today's sales
- Monthly sales
- Sales trends
- Low-stock products
- Top-selling products
- Inventory value by category
- Estimated profit
- Sales reports
- Inventory reports

---

🏗️ Technology Stack

Layer| Technology
Frontend| HTML, CSS, Vanilla JavaScript
UI Charts| Chart.js
Authentication| Supabase Auth
Backend| FastAPI
Language| Python
Database| PostgreSQL via Supabase
ORM| SQLAlchemy
Database Security| Supabase Row Level Security
API Authentication| Supabase access tokens
Deployment| Compatible with services such as Render
Database Region| Supabase "ap-south-1"

---

🔐 Architecture

                    ┌──────────────────────┐
                    │      Browser         │
                    │ HTML / CSS / JS      │
                    └──────────┬───────────┘
                               │
                    ┌──────────┴───────────┐
                    │                      │
               Login/Signup          Application API
                    │                      │
                    ▼                      ▼
             ┌─────────────┐       ┌─────────────┐
             │  Supabase   │       │   FastAPI   │
             │    Auth     │       │   Backend   │
             └─────────────┘       └──────┬──────┘
                                          │
                                          ▼
                                  ┌───────────────┐
                                  │   Supabase    │
                                  │  PostgreSQL   │
                                  └───────────────┘

Authentication flow

1. User signs in or registers using Supabase Auth.
2. Supabase returns an access token.
3. The frontend stores the authenticated session.
4. API requests send the access token as a Bearer token.
5. FastAPI validates the token.
6. FastAPI identifies the user's profile and role.
7. Role-based dependencies enforce permissions.
8. Business operations are performed against PostgreSQL.

---

📁 Project Structure

backend/
├── app/
│   ├── main.py
│   ├── config.py
│   ├── database.py
│   ├── supabase_client.py
│   ├── security.py
│   ├── deps.py
│   ├── models.py
│   ├── schemas.py
│   │
│   └── routers/
│       ├── products.py
│       ├── sales.py
│       ├── purchases.py
│       ├── suppliers.py
│       ├── customers.py
│       ├── users.py
│       └── ...
│
├── seed.py
├── requirements.txt
└── .env.example

frontend/
├── index.html
├── login.html
├── register.html
├── dashboard.html
├── products.html
├── sales.html
├── purchases.html
├── customers.html
├── reports.html
├── ...
│
├── css/
│   └── ...
│
└── js/
    ├── api.js
    └── ...

database/
└── migrations/
    ├── ...
    └── ...

---

⚙️ Installation

1. Clone the project

git clone <repository-url>
cd the-blue-moon

---

2. Configure Supabase

Create a Supabase project and obtain the required credentials.

The backend requires:

- "SUPABASE_URL"
- "SUPABASE_ANON_KEY"
- "SUPABASE_SERVICE_ROLE_KEY"
- "DATABASE_URL"

The service-role key must remain server-side and must never be exposed through the frontend.

---

3. Configure environment variables

cd backend
cp .env.example .env

Configure the variables in ".env".

Example:

SUPABASE_URL=https://your-project.supabase.co
SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

DATABASE_URL=postgresql+psycopg2://postgres.PROJECT_REF:PASSWORD@aws-0-ap-south-1.pooler.supabase.com:6543/postgres

Database connection

The project is configured to work with the Supabase Transaction Pooler.

The connection URL should use SQLAlchemy's PostgreSQL driver format:

postgresql+psycopg2://...

Do not commit ".env" to Git.

---

🗄️ Database

The "database/migrations/" directory contains the SQL migrations used to create the application's database structure.

The database contains the major entities required by the application, including:

- Profiles
- Customers
- Products
- Categories
- Brands
- Suppliers
- Purchases
- Purchase items
- Sales
- Sale items
- Payments
- Returns
- Credit records
- Supporting role/security structures

The schema is designed around relational database principles with foreign-key relationships and appropriate constraints.

---

🌱 Seed Demo Data

After configuring the environment:

cd backend
pip install -r requirements.txt
python seed.py

The seed script creates demo authentication users and sample business data.

It can be used to quickly populate a development environment.

«⚠️ Do not use demo credentials or seed data as production credentials.»

---

▶️ Run Locally

From the "backend" directory:

uvicorn app.main:app --reload

Open:

http://127.0.0.1:8000/

FastAPI serves the frontend, so a separate frontend development server is not required.

---

🔐 Security

Security was treated as a core part of the application rather than only a frontend concern.

Authentication

- Supabase Auth handles authentication.
- Backend requests require valid authentication tokens.
- Access tokens are validated by FastAPI.
- Protected routes use authentication dependencies.

Authorization

The backend implements role-based authorization.

Examples include:

get_current_user
require_staff
require_admin

This prevents frontend-only permission checks from being treated as the application's security boundary.

Database Security

Supabase Row Level Security (RLS) is enabled as an additional layer of protection.

The backend also enforces application-level authorization before performing protected operations.

Secrets

Sensitive credentials such as:

- Database passwords
- Supabase service-role keys

are kept in environment variables and are not intended for frontend use.

The service-role key must never be committed to the repository.

---

🧪 Testing & Verification

The application has been tested after development and deployment configuration.

Testing covered the application's core functionality, including:

- Authentication
- Registration
- Login
- Role-based access
- Product management
- Inventory operations
- POS/sales operations
- Purchases
- Suppliers
- Customers
- Credit functionality
- Returns
- Reports
- Backend API behavior
- Database integration
- Frontend/backend communication
- Responsive interface behavior

The project was also checked using online security-testing tools.

Security test result

Overall security assessment: A+

The application was reviewed for common web/API security issues, with the implemented security controls including authentication, authorization, security headers, input validation, protected API routes, and database security controls.

«Security testing provides additional confidence but does not guarantee that an application is completely vulnerability-free. Production deployments should continue to receive dependency updates, monitoring, and periodic security testing.»

---

📈 Business Workflow

Product workflow

Category / Brand
       ↓
    Product
       ↓
    Inventory

Purchase workflow

Supplier
   ↓
Purchase
   ↓
Purchase Items
   ↓
Stock increases

Sales workflow

Customer
   ↓
POS Cart
   ↓
Sale
   ↓
Sale Items
   ↓
Payment
   ↓
Stock decreases

Credit workflow

Credit Sale
     ↓
Customer Balance
     ↓
Payment Recording
     ↓
Outstanding Balance decreases

Return workflow

Original Sale
     ↓
Return
     ↓
Stock adjustment
     ↓
Financial adjustment

---

📊 Reports

The dashboard provides business information such as:

- Daily sales
- Monthly sales
- Sales trends
- Top products
- Low-stock products
- Inventory valuation
- Category-level inventory
- Estimated profit

These reports are intended to help a small business owner monitor day-to-day operations without requiring separate accounting spreadsheets.

---

📱 Responsive Design

The frontend is designed to work across:

- Mobile phones
- Tablets
- Laptops
- Desktop computers

The interface uses responsive CSS while maintaining the application's visual identity and navigation structure.

---

☁️ Deployment

The application can be deployed using a Python-compatible hosting platform.

A typical deployment architecture is:

                    Internet
                       │
                       ▼
              ┌─────────────────┐
              │   Web Browser   │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │     Render      │
              │    FastAPI      │
              └────────┬────────┘
                       │
                       ▼
              ┌─────────────────┐
              │    Supabase     │
              │ Auth + Postgres │
              └─────────────────┘

Environment variables should be configured through the hosting provider rather than committing production secrets to the repository.

---

📝 Supabase Project Name

The Supabase project may still appear under its original internal project name, BookBridge POS, in the Supabase dashboard.

This does not affect the application branding.

The user-facing application is branded as:

«The Blue Moon»

The Supabase dashboard project name can be changed from the Supabase project settings if desired.

---

🎯 Project Summary

The Blue Moon combines the main functionality required by a small retail business into a single web application:

                    THE BLUE MOON
                          │
       ┌──────────────────┼──────────────────┐
       │                  │                  │
    Inventory           Sales             Customers
       │                  │                  │
    Products             POS             Credit
    Categories         Billing           History
    Brands              Returns          Payments
       │                  │                  │
       └──────────────────┼──────────────────┘
                          │
                    ┌─────┴─────┐
                    │           │
                Purchases    Reports
                    │           │
                Suppliers   Dashboard
                    │           │
                    └─────┬─────┘
                          │
                    Supabase DB

The result is a full-stack business management system with:

- 🔐 Authentication & authorization
- 👥 Role-based user management
- 📦 Inventory management
- 🛒 POS billing
- 💳 Multiple payment methods
- 🧾 Returns
- 🚚 Supplier & purchase management
- 💰 Customer credit
- 📊 Business reports
- 🗄️ PostgreSQL database
- 🔒 RLS and backend authorization
- 📱 Responsive frontend
- 🚀 Production deployment support

---

Status

Project status: Functional and tested

Security assessment: A+

Backend: FastAPI / Python
Frontend: HTML / CSS / JavaScript
Database: Supabase PostgreSQL
Authentication: Supabase Auth
Architecture: Full-stack web application

📜 Commercial License

The Blue Moon is distributed under a Proprietary Commercial License.

The source code is provided to the purchaser under a limited, non-transferable license for use in their own business or projects.

💵 License Price

Commercial Source-Code License: USD $49

The purchase price grants the buyer the rights described below for the purchased version of The Blue Moon.

---

✅ What the Buyer Is Allowed to Do

The purchaser may:

- Use the software for personal or commercial business purposes.
- Install and operate the software on their own servers or hosting accounts.
- Modify the source code.
- Customize the UI, branding, features, database, and business logic.
- Fix bugs and security issues.
- Add new features.
- Integrate the software with their own services and systems.
- Create a customized internal version for their own organization.
- Use the modified version within their own business.

The purchaser may retain their modifications for their own internal use.

---

❌ What the Buyer Is NOT Allowed to Do

Without written permission from the copyright owner, the purchaser may not:

- Resell the original software.
- Resell the source code.
- Redistribute the source code.
- Upload the source code to public repositories.
- Publish the complete source code online.
- Give the source code to another person or company.
- Share the purchased source code with other buyers.
- Sell copies of the software.
- Sell access to the source code.
- Create a competing product based substantially on the software and sell it.
- Repackage the software and sell it under another name.
- Remove or alter the copyright and license notices.
- Use modifications as a way to redistribute or resell the software.
- Sell, sublicense, transfer, or otherwise commercially distribute the software or a modified version of it.

Modification does NOT grant resale rights

Modifying the source code does not create a new resale license.

For example:

«Buyer purchases The Blue Moon for $49 → modifies the dashboard, adds features, changes the design, and changes the branding.»

The buyer may use that modified version for their own business, but may not sell or redistribute that modified version to another person or business.

---

👨‍💻 Ownership

The software and its original source code remain the intellectual property of the copyright owner.

Purchasing a license does not transfer copyright ownership.

The buyer receives permission to use and modify the software according to this license.

Any original modifications created by the buyer remain subject to the restrictions of this license when they are based on, derived from, or incorporated into The Blue Moon.

---

🔒 Source Code Protection

The source code may be provided to the purchaser because modification and customization are part of the purchased license.

However, receiving the source code does not grant permission to:

- redistribute it,
- publish it,
- sell it,
- sublicense it,
- or provide it to another party.

---

📦 License Scope

Unless a separate written agreement is provided, one purchase grants a license to the individual or organization that purchased it.

A purchaser may use the software across their own development, testing, and production environments.

Use by unrelated third parties, resale to clients, or redistribution as a commercial product requires a separate commercial license or written permission from the copyright owner.

---

🏷️ Resale / Extended Commercial License

Businesses that want to:

- resell The Blue Moon,
- provide it to their customers,
- build and sell a SaaS based on it,
- redistribute modified versions,
- white-label it for resale,
- or include it in a commercial software product

must obtain a separate written commercial/reseller license.

Reseller and white-label licensing is not included in the $49 standard license.

Pricing for extended commercial rights is negotiated separately.

---

⚠️ License Violations

Unauthorized redistribution, resale, sublicensing, or publication of the source code constitutes a violation of this license.

If the license is violated, the copyright owner may terminate the purchaser's license and pursue any remedies available under applicable law.

Upon termination, the purchaser must stop distributing or using the software where required by applicable law and the terms of the termination.

---

📄 License Notice

Copyright © 2026 The Blue Moon.

All rights reserved.

This software is provided under the The Blue Moon Commercial License.

Standard License Price: USD $49

No resale, redistribution, sublicensing, or commercial redistribution rights are included unless explicitly granted in a separate written agreement.

---

«Important: This license is intended to describe the commercial terms for The Blue Moon. For actual commercial sales, especially international sales, have the final license reviewed by a qualified lawyer in the jurisdiction(s) where you sell the software.»