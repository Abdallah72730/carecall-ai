# CareCall AI — Claude Code Context

## What this project is
AI voice receptionist platform for dental and healthcare clinics in Alberta, Canada.
Answers inbound calls 24/7, captures after-hours messages, provides clinic admin portal.
Phase 1 of an 18-month product. Goal: 2 paying clients by end of week 12.

## Current phase
**Phase 1** — 12 weeks, solo developer, learning as we go.

## Tech stack — do not deviate without asking
| Layer | Technology | Notes |
|---|---|---|
| Voice pipeline | Vapi.ai | Handles Twilio + Deepgram STT + Cartesia TTS |
| LLM | Groq + Llama 3.3 70B | Primary. Cerebras Llama 3.3 70B is the US-based fallback. DeepSeek was retired pre-launch: PRC data residency vs PIPEDA + Alberta HIA. |
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | Local, free, 384 dims |
| Vector search | Supabase pgvector | No Pinecone in Phase 1 |
| Database | Supabase (PostgreSQL) | Free tier |
| Backend | Python 3.12 + FastAPI | Deployed on Railway.app |
| Frontend | Next.js 14 App Router + Tailwind CSS | Deployed on Vercel |
| Auth | Supabase Auth (email/password) | JWT, RLS policies |
| Email | Resend | After-hours message alerts |
| Payments | Stripe | CAD subscriptions, $99 pilot / $149 starter |
| File storage | Cloudflare R2 | Document uploads |
| Monitoring | Sentry + Better Stack | Error tracking + uptime |
| DNS | Cloudflare | Domain: carecallai.ca |

## Monorepo structure
```
carecall-ai/
├── backend/               # Python FastAPI
│   ├── main.py            # App entry, router registration, CORS
│   ├── config.py          # All env vars via python-dotenv
│   ├── db.py              # Supabase client singleton (anon + service role)
│   ├── routers/
│   │   ├── vapi.py        # POST /vapi/webhook, /vapi/llm, /vapi/end-of-call, /vapi/save-message
│   │   └── admin.py       # All /admin/* CRUD endpoints
│   ├── services/
│   │   ├── embedding.py   # get_embedding(), batch_encode()
│   │   ├── knowledge.py   # search_faqs(), format_context()
│   │   ├── hours.py       # is_clinic_open(), get_day_hours()
│   │   └── email.py       # send_message_alert()
│   ├── models/
│   │   └── vapi.py        # Pydantic models for Vapi webhook payloads
│   ├── db/
│   │   ├── schema.sql     # Full DDL — all tables, indexes, RLS
│   │   └── migrations/    # Versioned: 001_initial.sql, 002_*.sql
│   ├── scripts/
│   │   └── seed_faqs.py   # Seeds 30 dental clinic FAQs with embeddings
│   ├── tests/
│   │   ├── unit/          # pytest unit tests per service
│   │   ├── integration/   # Integration tests against staging Supabase
│   │   └── fixtures/      # Sample Vapi webhook JSON payloads
│   ├── requirements.txt
│   ├── .env.example
│   └── Procfile           # web: uvicorn main:app --host 0.0.0.0 --port $PORT
├── frontend/              # Next.js 14
│   ├── app/
│   │   ├── layout.tsx
│   │   ├── page.tsx       # Landing page
│   │   ├── login/page.tsx
│   │   ├── pricing/page.tsx
│   │   └── dashboard/
│   │       ├── layout.tsx         # Sidebar + header shell
│   │       ├── page.tsx           # Stats overview
│   │       ├── faqs/page.tsx      # FAQ CRUD table + modal
│   │       ├── hours/page.tsx     # 7-day hours grid
│   │       ├── calls/page.tsx     # Call logs with filters
│   │       └── messages/page.tsx  # After-hours messages
│   ├── components/
│   │   ├── layout/        # Sidebar, Header, MobileNav
│   │   └── ui/            # FAQTable, FAQModal, HoursGrid, MessageCard, StatsCard, Toast
│   ├── lib/
│   │   ├── supabase/
│   │   │   ├── client.ts  # Browser Supabase client
│   │   │   └── server.ts  # Server-side Supabase client (SSR)
│   │   └── useClinic.ts   # Hook: fetches clinic row for authenticated user
│   └── middleware.ts      # Auth protection for /dashboard/* routes
├── docs/
│   ├── adr/               # Architecture Decision Records
│   ├── prompts/           # Vapi system prompt versions
│   └── vapi-samples/      # Sample webhook payloads
├── CLAUDE.md              # This file
├── .gitignore
└── README.md
```

## Database schema — 5 tables
```sql
-- 1. clinics (one row per business)
id uuid PK, name text, phone_number text, email text,
vapi_assistant_id text, user_id uuid (FK to auth.users),
subscription_status text, emergency_number text,
is_active bool DEFAULT true, created_at timestamptz

-- 2. clinic_hours (7 rows per clinic)
id uuid PK, clinic_id uuid FK, day_of_week int (0=Mon 6=Sun),
open_time time, close_time time, is_closed bool, timezone text DEFAULT 'America/Edmonton'

-- 3. faq_entries (knowledge base)
id uuid PK, clinic_id uuid FK, question text, answer text,
category text, embedding vector(384), created_at timestamptz, updated_at timestamptz

-- 4. call_logs (every call)
id uuid PK, clinic_id uuid FK, vapi_call_id text,
started_at timestamptz, ended_at timestamptz, duration_seconds int,
was_after_hours bool, call_summary text, caller_number text

-- 5. after_hours_messages (captured messages)
id uuid PK, clinic_id uuid FK, call_log_id uuid FK,
caller_name text, caller_phone text, message_reason text,
captured_at timestamptz, email_sent bool DEFAULT false, is_read bool DEFAULT false
```

## Backend API endpoints
```
GET  /health                     -> {status, db}
POST /vapi/chat/completions      -> Groq proxy (OpenAI-compatible streaming)
POST /vapi/webhook               -> Main Vapi tool call handler (get_clinic_info, save_message)
POST /vapi/end-of-call           -> Call logging
POST /vapi/save-message          -> After-hours message persistence + email + Telegram
GET  /admin/faqs                 -> List FAQs for clinic (JWT required)
POST /admin/faqs                 -> Create FAQ, auto-embeds (JWT required)
PUT  /admin/faqs/{id}            -> Update FAQ, re-embeds if content changed (JWT required)
DELETE /admin/faqs/{id}          -> Delete FAQ (JWT required)
POST /billing/checkout           -> Create Stripe Checkout session (JWT required)
POST /billing/portal             -> Create Stripe Customer Portal session (JWT required)
POST /billing/webhook            -> Stripe event handler (signature-verified)
```

Note: dashboard data (stats, hours, call logs, messages) is read directly from Supabase
by the Next.js server components via RLS — there are no `/admin/stats`, `/admin/hours`,
`/admin/calls`, or `/admin/messages` backend endpoints.

## Vapi integration details
- Vapi server URL: `https://api.yourdomain.ca/vapi/webhook`
- Custom LLM URL: `https://api.yourdomain.ca/vapi/llm`
- End-of-call URL: `https://api.yourdomain.ca/vapi/end-of-call`
- Tool 1: `get_clinic_info` — params: `{query: string}` — fires on every FAQ question
- Tool 2: `save_message` — params: `{caller_name, caller_phone, message_reason}` — fires after-hours capture
- Voice: Cartesia Sonic (via Vapi)
- STT: Deepgram Nova-2 (via Vapi)
- LLM: custom (points to /vapi/llm -> Groq llama-3.3-70b-versatile)

## Vapi webhook payload shape (function-call type)
```json
{
  "message": {
    "type": "function-call",
    "functionCall": {
      "name": "get_clinic_info",
      "parameters": { "query": "what are your hours" }
    },
    "call": {
      "id": "call_abc123",
      "assistantId": "asst_xyz"
    }
  }
}
```
Response must be: `{"result": "<context string>"}`

## Embedding details
- Model: sentence-transformers/all-MiniLM-L6-v2
- Dimensions: 384
- Normalized: yes (`normalize_embeddings=True`)
- pgvector operator: `<=>` (cosine distance)
- Index: IVFFlat with `lists=100`
- Search query: `SELECT question, answer FROM faq_entries WHERE clinic_id = $1 ORDER BY embedding <=> $2 LIMIT 3`

## Environment variables (.env.example)
```
# Supabase
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=

# AI — Groq primary, Cerebras fallback. DeepSeek removed: PRC data
# residency conflicts with PIPEDA cross-border disclosure rules and
# Alberta Health Information Act expectations for clinic custodians.
GROQ_API_KEY=
CEREBRAS_API_KEY=

# Vapi
VAPI_API_KEY=

# Email
RESEND_API_KEY=
RESEND_FROM_EMAIL=noreply@carecallai.net

# Stripe
STRIPE_SECRET_KEY=
STRIPE_PUBLISHABLE_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_PILOT_PRICE_ID=
STRIPE_STARTER_PRICE_ID=

# Cloudflare R2
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=

# Sentry
SENTRY_DSN_BACKEND=
SENTRY_DSN_FRONTEND=

# App
FRONTEND_URL=https://app.carecallai.ca
TEST_CLINIC_ID=
SENTENCE_TRANSFORMERS_HOME=/tmp/models
```

## Python dependencies
```
fastapi
uvicorn[standard]
python-dotenv
supabase
httpx
sentence-transformers
resend
sentry-sdk[fastapi]
stripe
pytz
pydantic
pytest
pytest-cov
ruff
```

## Key constraints and rules
1. Every /admin/* endpoint requires valid Supabase JWT in Authorization header
2. Every DB query must filter by clinic_id — no cross-tenant data ever
3. Never store health information (symptoms, diagnoses, medications)
4. AI disclosure must be first utterance of every call
5. Embeddings auto-generated on every FAQ create/update — never stale
6. Groq is primary LLM. Cerebras (US-based) is the rate-limit/outage fallback. Never use DeepSeek (PRC data residency vs PIPEDA + Alberta HIA) and never use GPT-4o in Phase 1.
7. sentence-transformers model loaded ONCE at startup, not per-request
8. All errors caught in webhook handler — always return graceful fallback, never 500 to Vapi
9. Stripe webhooks verified with signature before processing
10. No hardcoded secrets — all via environment variables

## Build order (follow M0 -> M11 sequence)
- **M0**: repo + accounts + deploy both apps
- **M1**: database tables + RLS + Supabase client
- **M2**: Vapi assistant + first call + Groq LLM proxy
- **M3**: embedding service + FAQ CRUD API + seed 30 FAQs
- **M4**: full webhook integration — AI answers calls from DB
- **M5**: business hours + after-hours capture + email
- **M6**: Next.js auth (Supabase SSR) + route protection
- **M7**: admin portal UI (6 pages)
- **M8**: guardrails + compliance (health blocker, disclosure)
- **M9**: Sentry + Better Stack + error handling
- **M10**: Stripe billing + subscription gating
- **M11**: pilot onboarding + landing page + outreach

## Current status
M0–M11 shipped. Backend on Railway, frontend on Vercel (carecallai.ca).
Stripe billing, Sentry, Vapi per-clinic provisioning, blind/warm transfer all live.
Maintenance phase: ruff clean, ESLint clean, 47 unit tests green.

## Definition of Done (every task)
- Code linted (ruff for Python, ESLint for TS)
- Error handling covers all external API calls
- No hardcoded secrets
- Tested: manually verified the "done when" condition from task breakdown
- Logged: no `console.log` or `print()` left in production paths (use logging module)
