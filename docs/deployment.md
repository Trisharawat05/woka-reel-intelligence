# Woka Reel Intelligence — Deployment & Operations Guide

## 1. Quick Start via Docker Compose (Recommended)

To run the complete production-identical stack (PostgreSQL 16, Redis 7, FastAPI backend, Next.js frontend):

```bash
# 1. Clone repository
git clone <repo-url>
cd woka-reel-analyzer

# 2. Configure environment
cp .env.example .env

# 3. Start containers
docker-compose -f infra/docker-compose.yml up --build -d

# 4. Apply database migrations
docker-compose -f infra/docker-compose.yml exec backend alembic upgrade head
```

- **Frontend Application:** `http://localhost:3000`
- **Backend API Docs (Swagger):** `http://localhost:8000/api/v1/docs`
- **API Health Check:** `http://localhost:8000/api/health`

---

## 2. Local Manual Development Setup

### 2.1 Backend (Python 3.10+)
```bash
cd backend
python -m venv venv
.\venv\Scripts\activate   # Windows (or source venv/bin/activate on Unix)
pip install -r requirements.txt

# Run migrations
alembic upgrade head

# Seed initial creator account
python -m app.seed

# Start FastAPI server
uvicorn app.main:app --reload --port 8000
```

### 2.2 Frontend (Node 18+ or 20+)
```bash
cd frontend
npm install
npm run dev
```

---

## 3. Running Automated Test Suites

### 3.1 Backend Pytest Suite
```bash
cd backend
.\venv\Scripts\python -m pytest -v
```

### 3.2 Frontend Unit Tests & Production Build
```bash
cd frontend
npm test
npm run build
```

---

## 4. Environment Variables Reference

| Variable | Default (Dev) | Description |
|---|---|---|
| `ENVIRONMENT` | `development` | Deployment environment (`development`, `staging`, `production`) |
| `DEBUG` | `True` | FastAPI debug mode |
| `SECRET_KEY` | *(Set in .env)* | 64-char key for signing JWT tokens |
| `TOKEN_ENCRYPTION_KEY` | *(Set in .env)* | Base64-encoded 32-byte key for AES-256 token encryption |
| `DATABASE_URL` | `postgresql://woka:woka_dev_password_2026@localhost:5432/woka_reel_intelligence` | PostgreSQL connection string |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis broker and cache connection string |
| `META_APP_ID` | `""` | Official Meta App ID |
| `META_APP_SECRET` | `""` | Official Meta App Secret |
| `CORS_ORIGINS` | `["http://localhost:3000"]` | Allowed CORS origins array |
