# FindBack

**AI-powered lost, found, donation & community recovery platform.**

FindBack helps a community report lost belongings, publish found items, donate usable goods they no longer need, and get automatically paired with likely matches using AI — with ownership verification, in-app conversations, and notifications before anything changes hands.

[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React](https://img.shields.io/badge/React-19-61DAFB?logo=react&logoColor=black)](https://react.dev/)
[![TypeScript](https://img.shields.io/badge/TypeScript-6.0-3178C6?logo=typescript&logoColor=white)](https://www.typescriptlang.org/)
[![MySQL](https://img.shields.io/badge/MySQL-8.0-4479A1?logo=mysql&logoColor=white)](https://www.mysql.com/)
[![Python](https://img.shields.io/badge/Python-3.14-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-yellow.svg)](#license)

---

## Table of Contents

1. [Problem Statement](#problem-statement)
2. [Objectives](#objectives)
3. [Key Features](#key-features)
4. [Technologies Used](#technologies-used)
5. [System Architecture](#system-architecture)
6. [Project Structure](#project-structure)
7. [Setup](#setup)
8. [Environment Variables](#environment-variables)
9. [Running the Project](#running-the-project)
10. [API Documentation](#api-documentation)
11. [Authentication Flow](#authentication-flow)
12. [Main API Modules](#main-api-modules)
13. [Example API Usage](#example-api-usage)
14. [Testing](#testing)
15. [Git / GitHub Setup](#git--github-setup)
16. [Security Notes](#security-notes)
17. [Future Enhancements](#future-enhancements)
18. [Contributing](#contributing)
19. [License](#license)
20. [Developer](#developer)

---

## Problem Statement

Every day people lose personal belongings — wallets, bags, keys, laptops, phones — while others find those items but have no reliable way to return them. Existing solutions are fragmented (notice boards, social media posts, lost-and-found desks) and suffer from:

- **No structured data** — lost/found reports are free text and quickly buried.
- **No matching** — a person who found an item must manually scroll through unrelated posts.
- **No ownership verification** — scammers can claim items that are not theirs.
- **No safe handover channel** — people exchange contact details publicly or never connect.
- **No donation flow** — usable items people want to give away have no platform.

FindBack addresses all five problems in one platform.

## Objectives

1. Let users report **lost** and **found** items with structured details, photos, and location.
2. **Automatically match** lost reports against found reports using AI (text embeddings + image similarity + weighted scoring).
3. Let owners **verify ownership** through a claim workflow with verification questions before any return.
4. Let users **donate** usable items and let others **claim** them through a reviewed request flow.
5. Provide **in-app conversations** for matched pairs and claim threads — no personal contact exchange required.
6. Keep users informed with **notifications that deep-link** directly to the relevant match, claim, or report.
7. Allow the community to **report suspicious listings**, with an admin moderation queue.
8. Ensure **security**: hashed passwords, JWT auth, ownership enforced server-side, rate limiting.

## Key Features

Everything below is implemented and covered by tests or browser verification:

| Area | Features |
|---|---|
| **Listings** | Lost/found CRUD, images, categories, status (OPEN → MATCHED → RESOLVED), keyword search, filters (category, location, status, date, distance), pagination |
| **AI Matching** | Text embeddings with graceful fallback, vector index abstraction, weighted scoring (text/image/location/category), match explanations with score breakdown, background matching on create/update + manual rebuild |
| **Image Matching** | Magic-byte validated uploads, static `/media` serving, identical-image scoring, optional CLIP support |
| **Search** | Unified search across lost/found/donation (`GET /search`), nearby items by coordinates (`GET /nearby`), global stats (`GET /stats`) |
| **Donations** | Donation CRUD, filters, my-donations, claim endpoint |
| **Claims** | Create / approve / reject / cancel, claims received, verification answers, ownership verification, privacy |
| **Match Messaging** | Per-match conversation (finder ↔ loser), unread badges, read receipts, auto-advance POTENTIAL → CONTACTED on first message |
| **Claim Conversations** | Donor ↔ requester thread on any claim (including donations), parties-only access, remains available after approval as a handover channel |
| **Notifications** | List / unread-count / mark read / mark all, created on matches, claims, messages and reports; cards **deep-link** to the exact thread, claim or admin queue |
| **Reporting** | User-facing report creation + "my reports"; admin review queue |
| **Admin** | Platform stats, user suspend/activate/role changes, listing moderation, claims & reports review, global match rebuild |
| **Security** | bcrypt password hashing, JWT (expiry configurable), ownership always from the JWT (never the request body), sliding-window rate limiting with a stricter auth bucket, security headers, JSON-only 500s, CORS allow-list |

## Technologies Used

**Backend**
- **Python 3.14** / **FastAPI** — REST API, dependency injection, OpenAPI/Swagger
- **SQLAlchemy 2** (ORM) + **PyMySQL** — MySQL 8.0 database
- **python-jose** — JWT creation/verification · **passlib[bcrypt]** — password hashing
- **pydantic / pydantic-settings** — request/response schemas and configuration
- **Uvicorn** — ASGI server
- **pytest + httpx** — test suite (52 tests)

**Frontend**
- **React 19** + **TypeScript 6** + **Vite 8** — SPA
- **React Router 7** — routing (19 pages, protected & admin routes)
- **Tailwind CSS 4** (via `@tailwindcss/vite`) — styling with shared utilities
- **Axios** — HTTP client with JWT interceptor and automatic 401 logout

**Database** — MySQL 8.0 (9 tables: `users`, `lost_items`, `found_items`, `donations`, `claims`, `matches`, `messages`, `notifications`, `reports`)

**AI (all optional — the app works without them)**
- Sentence-transformers (`all-MiniLM-L6-v2`) for text embeddings, FAISS for the vector index
- Optional CLIP for image embeddings · Optional Google **Gemini API** for match explanations (falls back to built-in rule-based explanations when no key is set)

## System Architecture

```text
┌──────────────────────────────┐         ┌───────────────────────────────────┐
│  React SPA (Vite :5173)      │  HTTPS  │  FastAPI backend (:8000)          │
│  ├─ AuthContext (JWT in      │ ──────► │  ├─ Middleware: logging →         │
│  │   localStorage)           │  JSON   │  │   rate-limit → CORS →          │
│  ├─ Axios client (401 logout)│ ◄────── │  │   security headers             │
│  ├─ 19 pages (Router v7)     │         │  ├─ Routers (12): auth, lost,     │
│  └─ shared components        │         │  │   found, donations, claims,    │
└──────────────────────────────┘         │  │   search, matches, uploads,    │
                                         │  │   notifications, reports,      │
                                         │  │   admin, home                  │
                                         │  ├─ Services: matching, embedding,│
                                         │  │   image, claim, message,       │
                                         │  │   notification, vector store   │
                                         │  └─ Non-destructive migrations    │
                                         └───────────┬───────────────────────┘
                                                     │ SQLAlchemy
                                                     ▼
                                         ┌───────────────────────────┐
                                         │  MySQL 8.0 (`findback`)   │
                                         │  9 tables · additive-only │
                                         │  schema migrations        │
                                         └───────────────────────────┘
```

**Request lifecycle:** router validates via pydantic → auth dependency decodes the JWT and resolves the user → service layer applies business rules (ownership, claim states) → response. Schema changes at startup are **additive only** (`ALTER TABLE ADD COLUMN`, `CREATE INDEX`, `ADD CONSTRAINT` — never `DROP`/`TRUNCATE`).

## Project Structure

```text
opencodepj/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI entry point (middleware, routers, lifespan)
│   │   ├── config.py          # All settings from environment (.env)
│   │   ├── database.py        # Engine / session factory
│   │   ├── models.py          # SQLAlchemy models (9 tables)
│   │   ├── schemas.py         # Pydantic request/response schemas
│   │   ├── security.py        # bcrypt hashing, JWT encode/decode
│   │   ├── dependencies.py    # get_current_user / optional / require_admin
│   │   ├── middleware.py      # Rate limiting, security headers
│   │   ├── migrations.py      # Non-destructive schema sync (ensure_schema)
│   │   ├── routers/           # 12 API routers
│   │   ├── services/          # matching, embedding, image, claim, message,
│   │   │                      # notification, vector_store
│   │   └── utils/             # helpers, query builders, validators
│   ├── tests/                 # 52 pytest tests
│   ├── create_tables.py       # Safe table creation / additive migration
│   ├── promote_admin.py       # Promote a user to ADMIN: `python promote_admin.py <email>`
│   ├── requirements.txt
│   ├── .env.example           # Template (real .env is gitignored)
│   └── pytest.ini
├── frontend/
│   ├── src/
│   │   ├── main.tsx           # React entry + all routes
│   │   ├── App.tsx            # Layout (Navbar + Outlet + Footer)
│   │   ├── pages/             # 19 pages (Home, Lost, Found, Donations,
│   │   │                      #  Matches, Dashboard, Notifications, Admin…)
│   │   ├── components/        # Navbar, Footer, items, media, messages, ui
│   │   ├── context/           # AuthContext (JWT)
│   │   └── lib/               # api.ts (Axios), types.ts
│   ├── package.json / package-lock.json
│   └── .env.example           # VITE_API_BASE_URL template
├── MASTER_README.md           # Full specification & progress log
├── README.md                  # This file
└── .gitignore
```

## Setup

### Prerequisites

| Tool | Version used | Notes |
|---|---|---|
| Python | 3.14 (3.10+ should work) | virtualenv recommended |
| Node.js | 24 LTS (18+ required for Vite 8) | ships with npm |
| MySQL | 8.0 | server running locally |
| Git | any recent | |

### 1. Clone

```bash
git clone https://github.com/vinayyadav2208/FindBack.git
cd FindBack
```

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate          # Windows:  source venv/bin/activate on macOS/Linux
pip install -r requirements.txt
```

### 3. Frontend

```bash
cd frontend
npm install
```

## Environment Variables

**Backend — copy `backend/.env.example` to `backend/.env` and fill in real values:**

| Variable | Required | Purpose |
|---|---|---|
| `DATABASE_URL` | ✅ | `mysql+pymysql://USER:PASSWORD@localhost:3306/findback` |
| `SECRET_KEY` | ✅ | JWT signing secret — generate: `python -c "import secrets; print(secrets.token_hex(32))"` |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | | Token lifetime (default `1440`) |
| `ALGORITHM` | | JWT algorithm (default `HS256`) |
| `FRONTEND_URL` / `CORS_ORIGINS` | | Allowed origins (dev: `http://localhost:5173`) |
| `GEMINI_API_KEY` | | Optional — AI match explanations; app runs fine without it |
| `EMBEDDING_MODEL`, `MATCH_TOP_K`, `MATCH_MIN_SCORE` | | AI matching tuning |
| `RATE_LIMIT_*` | | Sliding-window rate limiting (auth bucket is stricter) |
| `W_TEXT`, `W_IMAGE`, `W_LOCATION`, `W_CATEGORY` | | Match scoring weights (sum ≈ 1.0) |
| `MEDIA_DIR`, `MAX_UPLOAD_SIZE_MB`, `DEBUG` | | Uploads & debug flag |

**Frontend — copy `frontend/.env.example` to `frontend/.env`:**

| Variable | Purpose |
|---|---|
| `VITE_API_BASE_URL` | Backend base URL (default `http://127.0.0.1:8000`) |

> ⚠️ **Never commit `.env`.** Real environment files are gitignored; only the `.env.example` templates (placeholders only) live in the repository.

## Running the Project

**1. Database** — make sure MySQL is running and the database exists:

```sql
CREATE DATABASE IF NOT EXISTS findback;
```

**2. Backend** (terminal 1):

```bash
cd backend
venv\Scripts\activate
python create_tables.py                # creates missing tables/columns only — never drops
python -m uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

**3. Frontend** (terminal 2):

```bash
cd frontend
npm run dev
```

Open **http://localhost:5173** — the dev server must use this origin so the backend CORS allow-list accepts it.

- API docs (Swagger): **http://127.0.0.1:8000/docs**
- Health check: **http://127.0.0.1:8000/health**

## API Documentation

Interactive Swagger UI is served at **`/docs`** (and ReDoc at `/redoc`) — every endpoint is documented there with schemas and auth. The API has **66 endpoints** across 12 routers:

| Method | Endpoint | Purpose |
|---|---|---|
| POST | `/auth/register`, `/users` | Register (JSON) — legacy alias kept |
| POST | `/auth/login`, `/login` | Login (JSON / OAuth2 form) — returns JWT |
| GET | `/me` | Current user from token |
| GET/POST | `/lost-items`, `/found-items` | List & create (filters: `q`, `category`, `location`, `status`, `date`, `distance`, `page`, `limit`) |
| GET/PUT/DELETE | `/lost-items/{id}`, `/found-items/{id}` | Detail & owner-only update/delete |
| GET | `/my-lost-items`, `/my-found-items` | Owner listings |
| GET/POST | `/donations`, `/donations/{id}`, `/donations/{id}/claim` | Donation CRUD + claim request |
| GET/POST | `/claims`, `/claims/{id}/approve|reject|cancel` | Claim workflow |
| GET/POST | `/claims/{id}/messages`, `/claims/{id}/messages/read` | Claim conversation |
| GET | `/search`, `/nearby`, `/stats` | Unified search, nearby by lat/lon, platform stats |
| GET/PUT | `/matches`, `/matches/{id}`, `/matches/{id}/status` | AI matches + status |
| GET/POST | `/matches/{id}/messages`, `/messages/read`, `/messages/unread-count` | Match conversation |
| POST | `/matches/rebuild`, `/admin/matches/rebuild` | Re-run AI matching |
| POST | `/uploads` | Image upload (magic-byte validated) |
| GET/PUT | `/notifications`, `/notifications/{id}/read`, `/notifications/read-all` | Notifications (deep-link fields) |
| POST/GET | `/reports`, `/reports/mine` | Report listings |
| GET/PUT | `/admin/*` | Stats, users, listings, claims, reports moderation |

## Authentication Flow

```text
POST /auth/register  ──►  bcrypt-hash password  ──►  create user
        │
        └──► returns JWT {user_id, email} (expires in ACCESS_TOKEN_EXPIRE_MINUTES)

POST /auth/login     ──►  verify bcrypt hash  ──►  issue JWT

Every protected request:
   Authorization: Bearer <token>
        │
        ▼
   dependencies.get_current_user
        ├─ python-jose decodes + verifies signature & expiry
        ├─ user id comes ONLY from the token (never from the request body)
        └─ suspended accounts (is_active = false) are rejected

Frontend:
   Axios interceptor attaches the token from localStorage ("findback_token")
   on every request; any 401 response clears the token and redirects to /login.
```

Roles: `USER` (default) and `ADMIN` (admin routes double-check server-side; promote with `python promote_admin.py <email>`).

## Example API Usage

Register and call a protected endpoint:

```bash
# 1. Register
curl -X POST http://127.0.0.1:8000/auth/register \
  -H "Content-Type: application/json" \
  -d '{"name":"Alice","email":"alice@example.com","password":"Str0ngPass!xyz"}'

# → {"access_token":"eyJ...","token_type":"bearer","user":{...}}

# 2. Use the token on a protected endpoint
export TOKEN="eyJ..."

# 3. Report a lost item
curl -X POST http://127.0.0.1:8000/lost-items \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Black leather wallet","description":"Brown card holder, ID inside",
       "category":"Documents","location":"Central Station","lat":17.385,"lon":78.4867}'

# 4. Search across lost/found/donation listings
curl "http://127.0.0.1:8000/search?q=wallet"

# 5. Check AI matches (score + explanation + conversation)
curl -H "Authorization: Bearer $TOKEN" http://127.0.0.1:8000/matches
```

Response conventions: list endpoints return `{items, total, page, limit, pages}`; mutations return `{message, ...}`; single resources are returned directly.

## Testing

```bash
cd backend
venv\Scripts\activate
python -m pytest -q
```

- **52 tests** covering auth, listings, search, donations & claims, matching, notifications & reports, match messaging, claim conversations, security, and admin/uploads.
- Tests run against a **separate** `findback_test` database (configured in `tests/conftest.py`) — your development data is never touched.
- Rate limiting is disabled during tests (`RATE_LIMIT_ENABLED=false`) so runs aren't flaky.

Frontend checks:

```bash
cd frontend
npm run lint        # oxlint
npm run build       # tsc -b && vite build  (must pass with no errors)
```

## Git / GitHub Setup

```bash
git clone https://github.com/vinayyadav2208/FindBack.git
cd FindBack

# create a feature branch
git checkout -b feature/my-change

# ...make changes, then verify
cd backend && python -m pytest -q
cd ../frontend && npm run build

git add .
git commit -m "feat: describe your change"
git push origin feature/my-change
```

Rules of this repository:
- **Never commit `.env`** — it is gitignored; only `.env.example` placeholders go in.
- Never commit `node_modules/`, `venv/`, `__pycache__/`, `dist/`, `media/` uploads, or log files (all gitignored).
- No force-pushing `main`.

## Security Notes

- **Passwords**: bcrypt-hashed (never stored or returned in plaintext).
- **Tokens**: JWT signed with `SECRET_KEY` from the environment; expiry configurable.
- **Ownership**: every update/delete derives `user_id` from the JWT — a forged body cannot touch another user's data; non-owners get 403, admins can moderate.
- **Rate limiting**: sliding-window per IP, with a stricter bucket on auth endpoints; 429s still carry CORS headers so browsers can read them.
- **Headers**: security headers (e.g. `X-Content-Type-Options`, frame denial) on every response.
- **Uploads**: validated by magic bytes (not just extension), size-limited, served from a static mount.
- **Errors**: unhandled exceptions return a generic JSON 500 — stack traces are logged server-side only.
- **CORS**: explicit allow-list (`http://localhost:5173` in dev), no wildcard with credentials.
- **Secrets**: `.env` is gitignored; real credentials never appear in this repository.

## Future Enhancements

These are **not implemented yet** — listed as a roadmap only:

- **WebSocket live messaging** — today unread counts/threads refresh on page load and navigation.
- **Production deployment** — nginx/HTTPS/gunicorn behind a reverse proxy (currently dev servers only).
- **Vitest frontend unit tests** — the frontend is verified by `tsc`, oxlint, production build, and end-to-end browser testing.
- **Alembic versioned migrations** — schema sync is additive-only by design; formal versioned migrations would allow safe rollbacks.
- **Admin report deep-links** — report notifications open the admin queue; row-level deep params pending.
- **Stronger AI packages** — optional sentence-transformers/FAISS/CLIP/Gemini are supported but not installed by default.
- **Email/Push delivery** for notifications (currently in-app only).

## Contributing

1. Fork the repository and create a feature branch from `main`.
2. Keep changes focused; follow the existing structure (routers → services → models).
3. Add/extend pytest tests for backend behavior changes.
4. Verify before pushing:
   ```bash
   cd backend && python -m pytest -q     # must stay green (52+ tests)
   cd frontend && npm run build          # must pass
   ```
5. Never commit secrets, `.env`, or generated files (`node_modules`, `venv`, `dist`, `media/`).
6. Open a pull request describing **what** changed and **why**.

## License

This project is released under the [MIT License](LICENSE).

## Developer

**Vinay Yadav**
GitHub: [https://github.com/vinayyadav2208](https://github.com/vinayyadav2208)

Built with FastAPI, React, and MySQL — full specification and development log in [`MASTER_README.md`](MASTER_README.md).
