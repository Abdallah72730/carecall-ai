-- Migration 003: Stripe identifiers on clinics + 'active' status value.
-- Idempotent. Run in Supabase SQL editor.

ALTER TABLE clinics ADD COLUMN IF NOT EXISTS stripe_customer_id     text;
ALTER TABLE clinics ADD COLUMN IF NOT EXISTS stripe_subscription_id text;
CREATE INDEX IF NOT EXISTS idx_clinics_stripe_customer ON clinics(stripe_customer_id);

-- Loosen subscription_status to include 'active' / 'trialing' / 'incomplete'
-- so Stripe statuses round-trip cleanly without translation.
ALTER TABLE clinics DROP CONSTRAINT IF EXISTS clinics_subscription_status_check;
ALTER TABLE clinics ADD CONSTRAINT clinics_subscription_status_check
  CHECK (subscription_status IN (
    'trial', 'trialing', 'active', 'pilot', 'starter',
    'past_due', 'incomplete', 'canceled'
  ));
