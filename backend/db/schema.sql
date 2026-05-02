-- CareCall AI — full schema snapshot.
-- Idempotent: safe to re-apply. Run in Supabase SQL editor on a fresh project.

-- 1. Extensions
CREATE EXTENSION IF NOT EXISTS vector;

-- 2. Tables

-- 2.1 clinics: one row per business
CREATE TABLE IF NOT EXISTS clinics (
  id                  uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id             uuid REFERENCES auth.users(id) ON DELETE CASCADE,
  name                text NOT NULL,
  phone_number        text,
  email               text,
  vapi_assistant_id   text,
  subscription_status text NOT NULL DEFAULT 'trial'
                        CHECK (subscription_status IN ('trial','pilot','starter','past_due','canceled')),
  emergency_number    text,
  is_active           boolean NOT NULL DEFAULT true,
  created_at          timestamptz NOT NULL DEFAULT now()
);

-- 2.2 clinic_hours: 7 rows per clinic (0=Mon..6=Sun)
CREATE TABLE IF NOT EXISTS clinic_hours (
  id            uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id     uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  day_of_week   smallint NOT NULL CHECK (day_of_week BETWEEN 0 AND 6),
  open_time     time,
  close_time    time,
  is_closed     boolean NOT NULL DEFAULT false,
  timezone      text NOT NULL DEFAULT 'America/Edmonton',
  UNIQUE (clinic_id, day_of_week)
);

-- 2.3 faq_entries: knowledge base with 384-dim embeddings
CREATE TABLE IF NOT EXISTS faq_entries (
  id          uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id   uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  question    text NOT NULL,
  answer      text NOT NULL,
  category    text,
  embedding   vector(384),
  created_at  timestamptz NOT NULL DEFAULT now(),
  updated_at  timestamptz NOT NULL DEFAULT now()
);

-- 2.4 call_logs: every call answered by the assistant
CREATE TABLE IF NOT EXISTS call_logs (
  id                uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id         uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  vapi_call_id      text UNIQUE,
  started_at        timestamptz NOT NULL DEFAULT now(),
  ended_at          timestamptz,
  duration_seconds  integer,
  was_after_hours   boolean NOT NULL DEFAULT false,
  call_summary      text,
  caller_number     text
);

-- 2.5 after_hours_messages: captured during off-hours
CREATE TABLE IF NOT EXISTS after_hours_messages (
  id              uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  clinic_id       uuid NOT NULL REFERENCES clinics(id) ON DELETE CASCADE,
  call_log_id     uuid REFERENCES call_logs(id) ON DELETE SET NULL,
  caller_name     text,
  caller_phone    text,
  message_reason  text,
  captured_at     timestamptz NOT NULL DEFAULT now(),
  email_sent      boolean NOT NULL DEFAULT false,
  is_read         boolean NOT NULL DEFAULT false
);

-- 3. Indexes (all queries filter by clinic_id)
CREATE INDEX IF NOT EXISTS idx_clinics_user            ON clinics(user_id);
CREATE INDEX IF NOT EXISTS idx_clinic_hours_clinic     ON clinic_hours(clinic_id);
CREATE INDEX IF NOT EXISTS idx_faqs_clinic             ON faq_entries(clinic_id);
CREATE INDEX IF NOT EXISTS idx_calls_clinic_started    ON call_logs(clinic_id, started_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_clinic_capt    ON after_hours_messages(clinic_id, captured_at DESC);
CREATE INDEX IF NOT EXISTS idx_messages_unread         ON after_hours_messages(clinic_id) WHERE is_read = false;

-- IVFFlat cosine index for FAQ similarity search
CREATE INDEX IF NOT EXISTS idx_faqs_embedding
  ON faq_entries USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- 4. updated_at trigger for faq_entries
CREATE OR REPLACE FUNCTION set_updated_at() RETURNS trigger AS $$
BEGIN
  NEW.updated_at = now();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS faq_entries_updated_at ON faq_entries;
CREATE TRIGGER faq_entries_updated_at
  BEFORE UPDATE ON faq_entries
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- 5. Row-Level Security — defense-in-depth on top of app-layer clinic_id filtering
ALTER TABLE clinics              ENABLE ROW LEVEL SECURITY;
ALTER TABLE clinic_hours         ENABLE ROW LEVEL SECURITY;
ALTER TABLE faq_entries          ENABLE ROW LEVEL SECURITY;
ALTER TABLE call_logs            ENABLE ROW LEVEL SECURITY;
ALTER TABLE after_hours_messages ENABLE ROW LEVEL SECURITY;

-- clinics: each user owns at most one row
DROP POLICY IF EXISTS clinics_owner_all ON clinics;
CREATE POLICY clinics_owner_all ON clinics
  FOR ALL TO authenticated
  USING (user_id = auth.uid())
  WITH CHECK (user_id = auth.uid());

-- child tables: scoped through clinics.user_id
DROP POLICY IF EXISTS clinic_hours_tenant_all ON clinic_hours;
CREATE POLICY clinic_hours_tenant_all ON clinic_hours
  FOR ALL TO authenticated
  USING (clinic_id IN (SELECT id FROM clinics WHERE user_id = auth.uid()))
  WITH CHECK (clinic_id IN (SELECT id FROM clinics WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS faq_entries_tenant_all ON faq_entries;
CREATE POLICY faq_entries_tenant_all ON faq_entries
  FOR ALL TO authenticated
  USING (clinic_id IN (SELECT id FROM clinics WHERE user_id = auth.uid()))
  WITH CHECK (clinic_id IN (SELECT id FROM clinics WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS call_logs_tenant_all ON call_logs;
CREATE POLICY call_logs_tenant_all ON call_logs
  FOR ALL TO authenticated
  USING (clinic_id IN (SELECT id FROM clinics WHERE user_id = auth.uid()))
  WITH CHECK (clinic_id IN (SELECT id FROM clinics WHERE user_id = auth.uid()));

DROP POLICY IF EXISTS after_hours_messages_tenant_all ON after_hours_messages;
CREATE POLICY after_hours_messages_tenant_all ON after_hours_messages
  FOR ALL TO authenticated
  USING (clinic_id IN (SELECT id FROM clinics WHERE user_id = auth.uid()))
  WITH CHECK (clinic_id IN (SELECT id FROM clinics WHERE user_id = auth.uid()));

-- Note: the service_role key bypasses RLS by design.
-- Backend webhook handlers (no user JWT) MUST filter by clinic_id explicitly.
