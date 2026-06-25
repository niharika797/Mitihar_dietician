# Mityahar — Local Development Setup

AI-powered dietetics platform. Three sub-apps: FastAPI backend, React doctor dashboard, Expo patient app.

> **For teammates using Claude:** paste this whole README into Claude and say _"help me set up the Mityahar project"_ — it has everything it needs to guide you step by step.

---

## Prerequisites

Install these before anything else:

| Tool | Version | Download |
|---|---|---|
| Python | 3.10+ | [python.org](https://www.python.org/downloads/windows/) — check "Add Python to PATH" |
| Docker Desktop | Latest | [docker.com](https://www.docker.com/products/docker-desktop/) — must be running in system tray |
| Node.js | 18+ | [nodejs.org](https://nodejs.org/) |
| pnpm | Latest | `npm install -g pnpm` after Node |

**Verify all four work:**
```powershell
python --version
docker --version
node --version
pnpm --version
```

---

## 1. Clone & Configure Environment

```powershell
git clone <repo-url>
cd Mitihar_dietician
```

Copy the environment template and fill it in:
```powershell
Copy-Item .env.example .env
```

Open `.env` and set these values (minimum required to run):

```env
# Database — must match docker-compose defaults exactly
DATABASE_URL=postgresql+asyncpg://admin:mityahar_dev@localhost:5432/mityahar_db
POSTGRES_PASSWORD=mityahar_dev

# Generate a real secret: python -c "import secrets; print(secrets.token_hex(32))"
SECRET_KEY=replace_with_32_char_hex_string

# Leave these as-is for local dev
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_MINUTES=10080
COOKIE_SECURE=False
ALLOW_HARD_DELETE=False
CORS_ORIGINS=http://localhost:3000,http://localhost:5173

# Get a free key at aistudio.google.com
GEMINI_API_KEY_1=your-gemini-key

# Seed script credentials — pick anything for local dev
ADMIN_SEED_EMAIL=admin@mityahar.com
ADMIN_SEED_PASSWORD=Admin@1234
ADMIN_SEED_NAME=Super Admin
TEST_ADMIN_EMAIL=admin@mityahar.com
TEST_ADMIN_PASSWORD=Admin@1234
TEST_DOCTOR_EMAIL=dr.ashok.mehta@mitihar.test
TEST_DOCTOR_PASSWORD=Doctor@1234
```

> **Note:** `GOOGLE_CLIENT_*`, `REDIS_URL`, `USDA_API_KEY` are optional for local dev. Leave them blank.

---

## 2. Start the Database (Docker)

Make sure Docker Desktop is open and running, then:

```powershell
docker-compose up -d
```

Verify it started correctly:
```powershell
docker ps --filter name=mityahar_postgres
```

Expected output:
```
NAMES               STATUS       PORTS
mityahar_postgres   Up N secs    0.0.0.0:5432->5432/tcp
```

Then confirm the DB accepts connections:
```powershell
docker exec mityahar_postgres pg_isready -U admin -d mityahar_db
```

Expected: `/var/run/postgresql:5432 - accepting connections`

**What Docker runs:** a single `postgres:15` container. The backend, frontend, and patient app all run natively on your machine — not in Docker.

**Data persists** in a Docker named volume (`mityahar_pg_data`). To wipe and start fresh:
```powershell
docker-compose down -v   # WARNING: deletes all data
docker-compose up -d
```

---

## 3. Python Backend Setup

```powershell
# Create virtualenv
python -m venv venv

# Activate it (Windows)
venv\Scripts\activate

# Install all dependencies
pip install -r requirements.txt
```

Your terminal prompt should now show `(venv)` prefix.

---

## 4. Run Database Migrations

```powershell
# Still inside (venv)
alembic upgrade head
```

This creates all tables in the database. Run this every time you pull new migrations from the repo.

---

## 5. Seed the Database

**Option A — Restore team snapshot (recommended, fast):**

> Run this INSTEAD OF `alembic upgrade head` (step 4) — the snapshot includes schema + data together. If you already ran alembic, that's fine too — constraint warnings are harmless, data still loads.

```powershell
docker exec -i mityahar_postgres psql -U admin -d mityahar_db < db-backups\mityahar_2026-06-24.sql
```

Takes ~30–60 seconds. Restores: food items, recipes, ingredients, patients, doctors, admins — matching IDs across the team. Skip to step 6 when done.

**Option B — Run seed scripts from scratch (slower, ~5 min):**

```powershell
python -m scripts.seed_admin          # creates the admin account
python -m scripts.seed_food_items     # base food/nutrition data
python -m scripts.seed_6k_recipes     # 6000+ recipes (takes ~2-3 min)
```

> `seed_6k_recipes` is slow on first run — prints progress, let it finish.
> Use Option B only if the snapshot is outdated or you want a clean slate.

---

## 6. Start the Backend

```powershell
python -m uvicorn app.main:app --reload --port 8001 --host 0.0.0.0
```

API docs available at: [http://localhost:8001/docs](http://localhost:8001/docs)

---

## 7. Doctor Dashboard (Web Frontend)

```powershell
cd mitihar-frontend\apps
pnpm install
pnpm dev
```

Opens at: [http://localhost:5173](http://localhost:5173)

---

## 8. Patient App (Mobile)

```powershell
cd mitihar-patient-app
pnpm install
pnpm start      # opens Expo dev server
```

Then scan the QR code with the **Expo Go** app on your phone, or press `a` for Android emulator / `i` for iOS simulator.

> **Important:** The patient app connects to the backend via your machine's LAN IP, not `localhost`. Check the Metro output for the correct IP and set it in `mitihar-patient-app/.env`:
> ```env
> EXPO_PUBLIC_API_URL=http://192.168.x.x:8001
> ```

---

## Connecting to the Database via pgAdmin 4

Download: [pgAdmin 4](https://www.postgresql.org/ftp/pgadmin/pgadmin4/v9.12/windows/)

Connection settings:
| Field | Value |
|---|---|
| Host | `localhost` |
| Port | `5432` |
| Database | `mityahar_db` |
| Username | `admin` |
| Password | `mityahar_dev` |

After connecting: expand **Servers → mityahar_db → Schemas → public → Tables** to explore the data.

---

## Database Schema

A schema-only SQL export (no real data) is at [`db-backups/schema_only.sql`](db-backups/schema_only.sql). Use it to understand table structure. Do **not** use it to restore — use `alembic upgrade head` instead (it's always up to date).

---

## Common Issues

**`POSTGRES_PASSWORD must be set` error on `docker-compose up`**
→ Your `.env` is missing `POSTGRES_PASSWORD=mityahar_dev`. Add it and retry.

**`asyncpg` connection refused**
→ DB container isn't running. Run `docker ps` to check. If missing, run `docker-compose up -d`.

**`alembic upgrade head` fails with "relation already exists"**
→ Run `alembic current` to check state. If stuck, ask a teammate — don't run `down -v` without confirming.

**Patient app can't reach backend**
→ Check `EXPO_PUBLIC_API_URL` in `mitihar-patient-app/.env`. Must be your LAN IP, not `localhost`.

**`pnpm: command not found`**
→ Run `npm install -g pnpm` then close and reopen your terminal.

---

## Architecture Quick Reference

```
Mitihar_dietician/
├── app/                    # FastAPI backend (port 8001)
│   ├── routers/            # API route handlers
│   ├── services/           # Business logic (meal_generator, etc.)
│   ├── models/             # SQLAlchemy ORM models
│   └── core/               # Config, DB, auth, security
├── mitihar-frontend/apps/  # React doctor + admin dashboard (port 5173)
├── mitihar-patient-app/    # Expo React Native patient app
├── alembic/                # DB migrations
├── scripts/                # Seed + maintenance scripts
├── db-backups/             # schema_only.sql (structure reference only)
├── docker-compose.yml      # PostgreSQL container only
├── requirements.txt        # Python deps (pinned)
└── .env.example            # Template — copy to .env
```

**Middleware stack (outermost → innermost):**
`SecurityHeaders` → `CORS` → `SubscriptionCheck` → `DoctorIsolation` → `AdminIPWhitelist`
