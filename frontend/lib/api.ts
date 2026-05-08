"use client";

import { createClient } from "./supabase/client";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "";

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
