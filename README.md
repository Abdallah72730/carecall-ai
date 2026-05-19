# CareCall AI

AI voice receptionist for dental and healthcare clinics in Alberta, Canada.
Answers inbound calls 24/7 with a knowledge base trained on the clinic's own
FAQs, captures after-hours messages with caller name + phone + reason, emails
the clinic, and provides a self-serve admin portal for FAQs, hours, calls,
and messages.

**Phase 1 — code complete.** All milestones M0–M11 from `CLAUDE.md` are
shipped. Remaining work is activation (Stripe live mode, custom domain DNS,
provisioning per-clinic Vapi assistants for pilot clients).

## Live deployments

| App | URL |
|---|---|
| Frontend (Vercel) | `https://app.carecallai.ca` (alias: `https://frontend-five-gray-57.vercel.app`) |
| Backend (Railway) | `https://backend-production-d0cf2.up.railway.app` (target: `api.carecallai.ca`) |
| Diagnostics | `/diag` on the frontend prints the resolved API base URL and a live `/health` probe |

## Monorepo layout

```
backend/                  Python 3.12 + FastAPI on Railway
  main.py                 App entry, router registration, CORS
  config.py               Env loader (python-dotenv)
  db.py                   Supabase service-role client singleton
  routers/
    vapi.py               /vapi/chat/completions (Groq proxy), /vapi/webhook,
                          /vapi/end-of-call, /vapi/save-message
    admin.py              /admin/faqs CRUD (JWT-protected)
    billing.py            /billing/checkout, /billing/portal, /billing/webhook
  services/
    embedding.py          sentence-transformers all-MiniLM-L6-v2 (384-dim)
    knowledge.py          search_faqs RPC + format_context
    clinics.py            assistant_id -> clinic_id cache, is_clinic_live()
    hours.py              is_clinic_open() with zoneinfo
    email.py              Resend wrapper for after-hours alerts
    notify.py             Telegram operator pings
  db/
    schema.sql            Canonical full schema snapshot
    migrations/           Versioned 001..004
  scripts/
    seed_faqs.py          Seeds a test clinic with 30 dental FAQs

frontend/                 Next.js 14 (App Router) + Tailwind on Vercel
  app/
    page.tsx              Landing — hero, features, footer
    pricing/              Pilot + Starter tiers, Stripe Checkout buttons
    login/                Email + password sign-in
    signup/               14-day pilot signup
    diag/                 Public env-var + /health diagnostic page
    dashboard/
      layout.tsx          Sidebar shell, auth-gated
      page.tsx            Overview stats (calls today/7d, messages 7d, unread)
      faqs/               CRUD table + modal
      hours/              7-day grid editor
      calls/              Call log table with filters
      messages/           After-hours messages with read state
  components/layout/      Sidebar (unread badge, billing portal link)
  lib/
    api.ts                Auth-attaching fetch wrapper, falls back to Railway URL
    supabase/             Browser + SSR Supabase clients
    useClinic.ts          Client hook for current-user's clinic row
  middleware.ts           Cookie-aware auth, redirects /dashboard to /login

docs/                     ADRs, Vapi prompts, sample webhook payloads
```

## Tech stack

| Layer | Service | Notes |
|---|---|---|
| Voice pipeline | Vapi.ai | Twilio + Deepgram Nova-2 STT + Cartesia Sonic TTS |
| LLM (primary) | Groq · Llama 3.3 70B Versatile | proxied via `/vapi/chat/completions` |
| LLM (fallback) | Cerebras Inference · Llama 3.3 70B | US-based, kicks in on Groq 429/5xx. DeepSeek deliberately not used — PRC data residency clashes with PIPEDA + Alberta HIA. |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | local, 384-dim, normalized |
| Vector search | Supabase pgvector, IVFFlat lists=100, cosine | RPC `search_faqs` |
| Database | Supabase Postgres | RLS on every tenant table |
| Auth | Supabase Auth (email + password) | SSR cookies via `@supabase/ssr` |
| Email | Resend | after-hours message alerts |
| Payments | Stripe | $99 CAD Pilot · $149 CAD Starter, Customer Portal enabled |
| File storage | Cloudflare R2 | S3-compatible, document uploads (not yet wired) |
| Monitoring | Sentry (backend + frontend) | + operator Telegram pings on milestones |
| DNS | Cloudflare | `carecallai.ca`, `app.carecallai.ca`, `api.carecallai.ca` |

## End-to-end flow

```
1. Patient calls the clinic's number
2. Vapi answers, plays the AI-disclosure first message
3. Vapi POSTs to /vapi/chat/completions for each turn
4. Proxy resolves clinic via vapi_assistant_id, injects:
   - top-3 FAQ matches via search_faqs RPC
   - OPEN/CLOSED status from clinic_hours
   - subscription gate (politely declines if canceled)
5. Groq generates the reply, streamed back to Vapi
6. If clinic is CLOSED: assistant collects name + phone + reason,
   reads them back, then calls save_message tool
7. /vapi/save-message inserts after_hours_messages row, emails clinic
   via Resend, flips email_sent flag
8. /vapi/end-of-call upserts the call into call_logs
9. Clinic admin sees everything in the dashboard
```

## Getting started (local)

### Backend

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
cp .env.example .env       # then fill in your keys
uvicorn main:app --reload
# -> http://localhost:8000/health -> {"status":"ok","db":true}
```

### Frontend

```powershell
cd frontend
npm install
cp .env.local.example .env.local   # then fill in NEXT_PUBLIC_* values
npm run dev
# -> http://localhost:3000
```

### Database

Apply migrations in the Supabase SQL Editor, in order:

1. `backend/db/schema.sql` — full initial DDL (fresh project only)
2. `backend/db/migrations/002_faq_search_rpc.sql` — vector similarity RPC
3. `backend/db/migrations/003_stripe_columns.sql` — Stripe identifiers + status widening
4. `backend/db/migrations/004_clinic_on_signup.sql` — auto-clinic-on-signup trigger
5. `backend/db/migrations/005_transfer_number.sql` — `transfer_number` column for live call handoff
6. `backend/db/migrations/006_signup_captures_transfer_number.sql` — signup trigger captures transfer number

### Running tests

```powershell
cd backend
# Always use the venv Python — system Python lacks tzdata (Windows)
.venv\Scripts\python -m pytest tests/ -q
```

### Seed the test clinic

```powershell
cd backend
.venv\Scripts\Activate.ps1
python scripts/seed_faqs.py
# Prints TEST_CLINIC_ID; copy into backend/.env and Railway env.
```

## Environment variables

### Backend (`backend/.env`, also set on Railway)

```
# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# LLM — Groq primary, Cerebras fallback. DeepSeek removed pre-launch
# because PRC data residency conflicts with PIPEDA / Alberta HIA for
# the clinic custodians who deploy this service.
GROQ_API_KEY=
CEREBRAS_API_KEY=        # optional but recommended once you have ≥3 clinics

# Voice
VAPI_API_KEY=

# Email
RESEND_API_KEY=
RESEND_FROM_EMAIL=noreply@carecallai.ca

# Billing
STRIPE_SECRET_KEY=                 # sk_test_... or sk_live_...
STRIPE_WEBHOOK_SECRET=             # whsec_...
STRIPE_PILOT_PRICE_ID=             # price_... ($99 CAD/mo)
STRIPE_STARTER_PRICE_ID=           # price_... ($149 CAD/mo)
STRIPE_PUBLISHABLE_KEY=            # not actually used by backend; kept for parity

# File storage
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=

# Monitoring
SENTRY_DSN_BACKEND=

# Operator pings (Telegram)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# App
FRONTEND_URL=https://app.carecallai.ca
TEST_CLINIC_ID=                                          # set from seed_faqs.py output
SENTENCE_TRANSFORMERS_HOME=/tmp/models
```

### Frontend (`frontend/.env.local`, also set on Vercel for all envs)

```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_BASE_URL=https://backend-production-d0cf2.up.railway.app
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=
NEXT_PUBLIC_STRIPE_PILOT_PRICE_ID=
NEXT_PUBLIC_STRIPE_STARTER_PRICE_ID=
NEXT_PUBLIC_SENTRY_DSN=
```

`lib/api.ts` falls back to the hardcoded Railway URL if `NEXT_PUBLIC_API_BASE_URL`
is missing, so the dashboard works even on a misconfigured deploy.

## API surface

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | none | `{status, db}` liveness + Supabase ping |
| POST | `/vapi/chat/completions` | none (Vapi-only) | OpenAI-compatible streaming proxy to Groq, with KB + hours injection |
| POST | `/vapi/webhook` | none (Vapi-only) | tool calls (`get_clinic_info`, `save_message`) + end-of-call |
| POST | `/vapi/end-of-call` | none | call_logs upsert |
| POST | `/vapi/save-message` | none | after_hours_messages insert + email + email_sent flag |
| GET | `/admin/faqs` | JWT | list FAQs for the current clinic |
| POST | `/admin/faqs` | JWT | create FAQ, auto-embed |
| PUT | `/admin/faqs/{id}` | JWT | update FAQ, re-embed if content changed |
| DELETE | `/admin/faqs/{id}` | JWT | delete FAQ |
| POST | `/billing/checkout` | JWT | create Stripe Checkout session |
| POST | `/billing/portal` | JWT | create Stripe Customer Portal session |
| POST | `/billing/webhook` | Stripe signature | subscription lifecycle events |

## Database schema

Five tenant tables, every child references `clinic_id`. RLS forces
`clinic_id IN (SELECT id FROM clinics WHERE user_id = auth.uid())` on every
non-service-role query.

- `clinics` — one per business; `user_id`, `subscription_status`, `vapi_assistant_id`, `stripe_customer_id`, `stripe_subscription_id`
- `clinic_hours` — 7 rows per clinic, weekday-indexed, `timezone` per row
- `faq_entries` — `question`, `answer`, `embedding` vector(384)
- `call_logs` — keyed on `vapi_call_id` unique
- `after_hours_messages` — links to `call_log_id`, `is_read` + `email_sent` flags

See `backend/db/schema.sql` for the full DDL.

## Deploy

Both apps redeploy from the project root via their respective CLIs:

```powershell
# Backend
cd backend
railway up --service backend --ci

# Frontend
cd frontend
vercel deploy --prod --yes
```

Env vars on Railway: `railway variables --service backend --set "K=V" --skip-deploys`
Env vars on Vercel: dashboard UI or `vercel env add` (interactive).

## Definition of done (per CLAUDE.md)

- Code linted (ruff for Python, ESLint for TS)
- Error handling around every external API call
- No hardcoded secrets — all via env vars
- "Done when" condition manually verified
- No `console.log` or `print()` left in production paths — `logging` only

## Auto-resume

A scheduled Claude Code task runs every 6 hours, picks up the next un-shipped
milestone or quality fix from `git log`, ships a commit, and pings the
operator on Telegram. Configured in `~/.claude/scheduled-tasks/carecall-ai-autoresume/SKILL.md`.
