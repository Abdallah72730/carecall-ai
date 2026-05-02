# CareCall AI

AI voice receptionist for dental and healthcare clinics in Alberta, Canada. Answers inbound calls 24/7, captures after-hours messages, provides a clinic admin portal.

**Phase 1** — 12-week solo build. Goal: 2 paying clients by end of week 12.

## Monorepo layout

```
backend/    Python 3.12 + FastAPI on Railway
frontend/   Next.js 14 (App Router) + Tailwind on Vercel
docs/       ADRs, Vapi prompts, sample webhook payloads
```

See [CLAUDE.md](./CLAUDE.md) for the full tech stack, schema, API surface, and build order (M0 → M11).

## Getting started

### Backend

```bash
cd backend
python -m venv .venv
. .venv/Scripts/activate   # Windows
pip install -r requirements.txt
cp .env.example .env       # then fill in secrets
uvicorn main:app --reload
```

### Frontend

```bash
cd frontend
npm install
cp .env.local.example .env.local   # then fill in secrets
npm run dev
```

## Current milestone

**M0** — repo scaffold, accounts, and first deploys. See `CLAUDE.md` for the full milestone list.
