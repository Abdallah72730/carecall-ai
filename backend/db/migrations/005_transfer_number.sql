-- Migration 005: clinic-side transfer destination for live call handoff.
-- Idempotent. Run in Supabase SQL editor.
--
-- The assistant uses this number with Vapi's built-in transferCall tool
-- when the caller wants a human and the clinic is currently OPEN. Leave
-- NULL to disable transfers (assistant always handles the call itself).

ALTER TABLE clinics
  ADD COLUMN IF NOT EXISTS transfer_number text;
