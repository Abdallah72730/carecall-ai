-- Migration 004: auto-create clinic row when an auth.users row is inserted.
-- Pulls clinic name + phone out of raw_user_meta_data set by the signup form.
-- Idempotent. Run in Supabase SQL editor.

CREATE OR REPLACE FUNCTION public.handle_new_clinic_user()
RETURNS trigger
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public
AS $$
BEGIN
  INSERT INTO public.clinics (user_id, name, phone_number, email, subscription_status)
  VALUES (
    NEW.id,
    COALESCE(NULLIF(NEW.raw_user_meta_data->>'clinic_name', ''), NEW.email),
    NULLIF(NEW.raw_user_meta_data->>'clinic_phone', ''),
    NEW.email,
    'trial'
  )
  ON CONFLICT DO NOTHING;
  RETURN NEW;
END;
$$;

DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_clinic_user();
