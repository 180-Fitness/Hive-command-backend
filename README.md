# Hive Backend

Flask API for **Hive Command**: a private, single-enterprise deployment where one parent organization operates many subsidiary **companies**. This is not multi-tenant SaaS—one install serves your enterprise only.

## Layout (mirrors a layered Flask backend)

```
hive-backend/
  app.py                 # Application factory, bootstrap seed
  config.py              # Enterprise defaults
  db.py
  controllers/           # Request handlers
  routes/                # Blueprints / HTTP mapping
  models/                # SQLAlchemy models + Marshmallow schemas
  util/                  # Shared helpers
  lib/                   # Auth, model loading
  migrations/            # Alembic / Flask-Migrate
```

## Domain model

| Concept | Purpose |
|--------|---------|
| **Enterprise** | The single parent tenant for this deployment |
| **Company** | A subsidiary or division under the enterprise |
| **AppUser** | People scoped to a company; `enterprise-admin` sees all companies |

Roles: `enterprise-admin`, `company-admin`, `member`.

## Quick start

1. Create a PostgreSQL database named `hive_command` (or set `DATABASE_NAME`).
2. Copy `.env.example` to `.env` and set credentials.
3. Install and bootstrap:

```bash
cd hive-backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
export HIVE_ADMIN_PASSWORD='YourSecurePass1'
python populate_db.py
python app.py
```

API listens on port **8090** by default. Health check: `GET /health`.

Default admin email is configured in `config.py` (`admin_email`).

## API notes (vs. generic org-based apps)

- Companies live at `/company` and `/companies`, not `/organization`.
- Users are listed per company at `/users/company/<company_id>`.
- Auth uses the same header convention: `auth: <uuid token>` from `POST /user/auth`.

Routes for tags, sprints, comments, time entries, import/export, search, and custom fields return **501** until you implement them; models and folder structure are in place.

## Docker

```bash
docker build -t hive-backend .
docker run --env-file .env -p 8090:8090 hive-backend
```
