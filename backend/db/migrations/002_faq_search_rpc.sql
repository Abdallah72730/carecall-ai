-- Migration 002: search_faqs RPC for vector similarity lookup.
-- Idempotent. Run in Supabase SQL editor.

CREATE OR REPLACE FUNCTION search_faqs(
  p_clinic_id      uuid,
  p_query_embedding vector(384),
  p_match_count    int DEFAULT 3
)
RETURNS TABLE (
  id        uuid,
  question  text,
  answer    text,
  category  text,
  distance  float
)
LANGUAGE sql STABLE AS $$
  SELECT
    id, question, answer, category,
    embedding <=> p_query_embedding AS distance
  FROM faq_entries
  WHERE clinic_id = p_clinic_id
    AND embedding IS NOT NULL
  ORDER BY embedding <=> p_query_embedding
  LIMIT p_match_count;
$$;
