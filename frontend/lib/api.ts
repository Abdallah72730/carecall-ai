"use client";

import { createClient } from "./supabase/client";

// Defaults to the Phase 1 Railway deployment so local dev and any deploy
// without NEXT_PUBLIC_API_BASE_URL set still talks to a real backend.
const DEFAULT_API_BASE = "https://backend-production-d0cf2.up.railway.app";
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE;

async function authHeader(): Promise<HeadersInit> {
  const supabase = createClient();
  const {
    data: { session },
  } = await supabase.auth.getSession();
  return session?.access_token
    ? { Authorization: `Bearer ${session.access_token}` }
    : {};
}

export async function api<T = unknown>(
  path: string,
  init: RequestInit = {},
): Promise<T> {
  const auth = await authHeader();
  const url = `${API_BASE}${path}`;
  let res: Response;
  try {
    res = await fetch(url, {
      ...init,
      headers: {
        "Content-Type": "application/json",
        ...auth,
        ...(init.headers ?? {}),
      },
    });
  } catch (err) {
    throw new Error(
      `Network error reaching ${url || "(empty API base)"} — ` +
        `check NEXT_PUBLIC_API_BASE_URL on this deploy and CORS on the backend.`,
    );
  }
  if (!res.ok) {
    const text = await res.text().catch(() => "");
    throw new Error(text || `${res.status} ${res.statusText} on ${url}`);
  }
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}
