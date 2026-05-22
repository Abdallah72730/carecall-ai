# CareCall AI

AI **after-hours receptionist** for dental and healthcare clinics in Alberta,
Canada. Sits as the safety net behind the clinic's existing reception line:
during business hours patients reach the human front desk as usual; outside
business hours / weekends / when the line is busy, calls roll over to the AI,
which answers FAQ-style questions from the clinic's own knowledge base, takes
detailed messages (name + phone + reason), emails the clinic, and escalates
true emergencies via blind-transfer to the on-call dentist.

**Phase 1 — code complete.** All milestones M0–M11 from `CLAUDE.md` are
shipped. Remaining work is activation (Stripe Live mode, custom domain DNS,
provisioning per-clinic Vapi assistants + phone numbers for pilot clients).

## Live deployments

| App | URL |
|---|---|
| Frontend (Vercel) | `https://carecallai.net` (alias: `https://frontend-five-gray-57.vercel.app`) |
| Backend (Railway) | `https://api.carecallai.net` (current: `https://backend-production-d0cf2.up.railway.app`) |
| Diagnostics | `/diag` on the frontend prints the resolved API base URL and a live `/health` probe |

## Telephony topology — one Vapi number + one Vapi assistant per clinic

Each clinic gets:

- A dedicated **Vapi assistant** (its own system prompt, FAQs, hours, voice, transfer destination)
- A dedicated **Vapi phone number** (the line that rings the AI)
- A row in `clinics` linking the two via `vapi_assistant_id` and storing the receptionist's direct line in `transfer_number`

The clinic publishes their existing number and uses telco-side conditional
call forwarding (Telus / Shaw / Rogers) to roll calls over to the Vapi number
**only when the receptionist can't pick up** — busy, no-answer, or outside
business hours. Daytime calls reach the human front desk with zero AI cost.

```
Patient dials  +1 403 OLD-OLD-OLD  (clinic's published number)
        │
        ├── Receptionist available  →  human picks up.  No AI involvement.
        │
        └── Busy / no-answer / after-hours
                ├──> Telco forwards to  +1 587 NEW-NEW-NEW  (Vapi number)
                │
                ▼
          Vapi assistant   ── KB + hours + subscription gate injected ──> Groq → Cerebras (fallback)
                │
                ├── Routine question  →  answer from knowledge base
                ├── Caller wants emergency contact  →  blind-transfer to transfer_number
                │   (AI session ends, Vapi stops billing AI minutes)
                └── Otherwise →  collect name + phone + reason
                                  →  save_message  →  email + Telegram + dashboard
```

## Monorepo layout

```
backend/                  Python 3.12 + FastAPI on Railway
  main.py                 App entry, router registration, CORS, model warmup on startup
  config.py               Env loader (python-dotenv)
  db.py                   Supabase service-role client singleton
  routers/
    vapi.py               /vapi/chat/completions (Groq→Cerebras proxy), /vapi/webhook,
                          /vapi/end-of-call, /vapi/save-message
    admin.py              /admin/faqs CRUD (JWT-protected)
    billing.py            /billing/checkout, /billing/portal, /billing/webhook
  services/
    embedding.py          sentence-transformers all-MiniLM-L6-v2 (admin-write side only)
    knowledge.py          get_all_faqs (cached, inlined into prompt) + search_faqs (kept for later)
    clinics.py            assistant_id -> clinic_id cache, is_clinic_live, get_transfer_number
    hours.py              is_clinic_open() with zoneinfo
    email.py              Resend wrapper for after-hours alerts
    notify.py             Telegram operator pings (autoresume cron only)
    vapi_provision.py     create_assistant_for_clinic, update_assistant_transfer
  db/
    schema.sql            Canonical full schema snapshot
    migrations/           Versioned 001..006
  scripts/
    seed_faqs.py                       Seeds the test clinic with 30 dental FAQs
    provision_pending_assistants.py    Provisions Vapi assistants for any clinic without one

frontend/                 Next.js 14 (App Router) + Tailwind on Vercel
  app/
    page.tsx              Landing — hero, features, footer
    pricing/              Pilot + Starter tiers, Stripe Checkout buttons
    login/                Email + password sign-in
    signup/               Pilot signup — captures clinic name, phone, optional transfer_number
    diag/                 Public env-var + /health diagnostic page
    dashboard/
      layout.tsx          Sidebar shell, auth-gated
      page.tsx            Overview stats (calls today/7d, messages 7d, unread)
      faqs/               CRUD table + modal
      hours/              7-day grid editor
      calls/              Call log table with filters
      messages/           After-hours messages with read state
  components/layout/      Sidebar (unread badge, billing portal link, Plans link)
  lib/
    api.ts                Auth-attaching fetch wrapper, falls back to hardcoded Railway URL
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
| Embeddings | sentence-transformers all-MiniLM-L6-v2 | local, 384-dim, normalized. Used only on FAQ create/update; the live voice path inlines the full KB to avoid Railway shared-CPU latency. |
| Database | Supabase Postgres | RLS on every tenant table |
| Auth | Supabase Auth (email + password) | SSR cookies via `@supabase/ssr` |
| Email | Resend | after-hours message alerts |
| Payments | Stripe | $99 CAD Pilot · $149 CAD Starter, Customer Portal enabled |
| File storage | Cloudflare R2 | S3-compatible, document uploads (not yet wired) |
| Monitoring | Sentry (backend) + Telegram pings | frontend Sentry env-var wired, not actively used |
| DNS | Cloudflare | `carecallai.net`, `app.carecallai.net`, `api.carecallai.net` |

## End-to-end LLM-proxy flow per turn

```
1. Vapi POSTs the OpenAI-compatible chat-completion to /vapi/chat/completions
2. Proxy strips Vapi-specific fields (assistant, call, customer, …) Groq would 400 on
3. Proxy resolves clinic via vapi_assistant_id (cached, lru)
4. Subscription gate — if clinic is canceled/disabled, single canned reply
5. KB injection — get_all_faqs(clinic_id) (cached 5 min), entire FAQ list goes
   into a system message ahead of the user turn
6. Open/closed status injected as a second system message:
     - OPEN + transfer_number  → answer in one sentence; if caller asks for a
                                 person, call transferCall tool (blind transfer)
     - OPEN + no transfer      → answer in one sentence; otherwise take a message
     - CLOSED                  → take a message via save_message tool
7. Forward to Groq; on 429/5xx/transport error fall back to Cerebras with same payload
8. Stream response back to Vapi unchanged
9. If LLM emits save_message → /vapi/save-message inserts into after_hours_messages,
   sends Resend email, flips email_sent
10. If LLM emits transferCall → Vapi blind-transfers to clinic.transfer_number,
    AI session ends, Vapi stops billing AI minutes
11. /vapi/end-of-call upserts the call_logs row keyed on vapi_call_id
12. Clinic admin sees the call + message in the dashboard
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
2. `backend/db/migrations/002_faq_search_rpc.sql` — vector similarity RPC (kept for future, not used on live path)
3. `backend/db/migrations/003_stripe_columns.sql` — Stripe identifiers + status widening
4. `backend/db/migrations/004_clinic_on_signup.sql` — auto-clinic-on-signup trigger
5. `backend/db/migrations/005_transfer_number.sql` — `transfer_number` column for live call handoff
6. `backend/db/migrations/006_signup_captures_transfer_number.sql` — signup trigger pulls transfer_number from metadata

### Seed the test clinic

```powershell
cd backend
.venv\Scripts\Activate.ps1
python scripts/seed_faqs.py
# Prints TEST_CLINIC_ID; copy into backend/.env and Railway env.
```

### Provision Vapi assistants for new clinics

```powershell
cd backend
.venv\Scripts\Activate.ps1
python scripts/provision_pending_assistants.py
# Iterates over clinics with NULL vapi_assistant_id and provisions one each.
# Idempotent.
```

After the script runs, buy a Vapi phone number in the dashboard and assign it
to the new assistant. (Number purchase is still manual until we add a payment
method to the Vapi account.)

### Running tests

```powershell
cd backend
# Always use the venv Python — system Python lacks tzdata on Windows
.venv\Scripts\python -m pytest tests/ -q
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
RESEND_FROM_EMAIL=noreply@carecallai.net

# Billing
STRIPE_SECRET_KEY=                 # sk_test_... or sk_live_...
STRIPE_WEBHOOK_SECRET=             # whsec_...
STRIPE_PILOT_PRICE_ID=             # price_... ($99 CAD/mo)
STRIPE_STARTER_PRICE_ID=           # price_... ($149 CAD/mo)
STRIPE_PUBLISHABLE_KEY=            # not used by backend; kept for parity

# File storage
R2_ACCOUNT_ID=
R2_ACCESS_KEY_ID=
R2_SECRET_ACCESS_KEY=
R2_BUCKET_NAME=

# Monitoring
SENTRY_DSN_BACKEND=

# Operator pings (Telegram — developer-facing only, not customer notifications)
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

# App
FRONTEND_URL=https://carecallai.net    # update once apex DNS resolves
TEST_CLINIC_ID=                         # from seed_faqs.py output
SENTENCE_TRANSFORMERS_HOME=/tmp/models
```

### Frontend (`frontend/.env.local`, also set on Vercel for all envs)

```
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_BASE_URL=https://api.carecallai.net   # falls back to Railway URL when unset
NEXT_PUBLIC_STRIPE_PUBLISHABLE_KEY=
NEXT_PUBLIC_STRIPE_PILOT_PRICE_ID=
NEXT_PUBLIC_STRIPE_STARTER_PRICE_ID=
NEXT_PUBLIC_SENTRY_DSN=
```

`lib/api.ts` falls back to the hardcoded Railway URL when `NEXT_PUBLIC_API_BASE_URL`
is empty, so the dashboard keeps working on a misconfigured deploy.

## API surface

| Method | Path | Auth | Purpose |
|---|---|---|---|
| GET | `/health` | none | `{status, db}` liveness + Supabase ping |
| POST | `/vapi/chat/completions` | none (Vapi-only) | OpenAI-compatible streaming proxy, Groq→Cerebras fallback, KB + hours + subscription injection |
| POST | `/vapi/webhook` | none (Vapi-only) | tool calls (`save_message`) + end-of-call passthrough |
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
non-service-role query. Service-role calls (webhook handlers, scripts) bypass
RLS but must filter by `clinic_id` in app code.

- `clinics` — one per business; `user_id`, `subscription_status`, `vapi_assistant_id`, `transfer_number`, `stripe_customer_id`, `stripe_subscription_id`
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

## Onboarding a new pilot clinic — end to end

1. Clinic signs up at `/signup`. Trigger creates the `clinics` row; their `transfer_number` (the on-call dentist's mobile) is captured if the box is checked.
2. Operator (or autoresume cron) runs `python scripts/provision_pending_assistants.py` from `backend/`. This creates the Vapi assistant via API and writes `vapi_assistant_id` back to the row.
3. Operator buys a Canadian-area-code Vapi phone number in the Vapi dashboard and assigns it to the new assistant. (~$1 USD/mo + per-minute usage. Will be scripted once Vapi payment method is on file.)
4. Operator emails the clinic the new Vapi number and instructs them to set up **conditional call forwarding** with their telco (Telus/Shaw/Rogers) so calls roll over to the AI when the line is busy, no-answer, or after-hours.
5. Clinic subscribes via `/pricing` → Stripe Checkout. Webhook flips `subscription_status` to `pilot` or `starter`.

## Definition of done (per CLAUDE.md)

- Code linted (ruff for Python, ESLint for TS)
- Error handling around every external API call
- No hardcoded secrets — all via env vars
- "Done when" condition manually verified
- No `console.log` or `print()` left in production paths — `logging` only

## Auto-resume

A scheduled Claude Code task runs every 6 hours, picks up the next un-shipped
milestone or quality fix from `git log`, ships a commit, and pings the
operator on Telegram. Configured in
`~/.claude/scheduled-tasks/carecall-ai-autoresume/SKILL.md`.
