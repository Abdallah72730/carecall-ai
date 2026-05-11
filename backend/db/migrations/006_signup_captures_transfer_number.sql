-- Migration 006: signup trigger also captures transfer_number.
-- Idempotent — replaces the function from migration 004 with a version
-- that pulls the optional clinic_transfer_number out of raw_user_meta_data
-- alongside clinic_name and clinic_phone.

CREATE OR REPLACE FUNCTION public.handle_new_clinic_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.clinics (
    user_id, name, phone_number, transfer_number, email, subscription_status
  )
  VALUES (
    NEW.id,
    COALESCE(NULLIF(NEW.raw_user_meta_data->>'clinic_name', ''), NEW.email),
    NULLIF(NEW.raw_user_meta_data->>'clinic_phone', ''),
    NULLIF(NEW.raw_user_meta_data->>'clinic_transfer_number', ''),
    NEW.email,
    'trial'
  )
  ON CONFLICT DO NOTHING;
  RETURN NEW;
END;
$$;

-- Trigger from migration 004 already references handle_new_clinic_user,
-- so the new body takes effect on next signup without re-binding.
