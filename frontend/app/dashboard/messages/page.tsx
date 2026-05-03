"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

type Message = {
  id: string;
  caller_name: string | null;
  caller_phone: string | null;
  message_reason: string | null;
  captured_at: string;
  is_read: boolean;
  email_sent: boolean;
};

export default function MessagesPage() {
  const [items, setItems] = useState<Message[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const { data, error: fetchErr } = await supabase
        .from("after_hours_messages")
        .select(
          "id,caller_name,caller_phone,message_reason,captured_at,is_read,email_sent",
        )
        .order("captured_at", { ascending: false })
        .limit(100);
      if (fetchErr) setError(fetchErr.message);
      else setItems((data as Message[]) || []);
      setLoading(false);
    }
    load();
  }, []);

  async function markRead(id: string) {
    const supabase = createClient();
    const { error: upErr } = await supabase
      .from("after_hours_messages")
      .update({ is_read: true })
      .eq("id", id);
    if (upErr) {
      setError(upErr.message);
      return;
    }
    setItems((prev) =>
      prev.map((m) => (m.id === id ? { ...m, is_read: true } : m)),
    );
  }

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">After-hours messages</h1>
      {error ? (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}

      {loading ? (
        <p className="text-slate-500">Loading...</p>
      ) : items.length === 0 ? (
        <p className="text-slate-500">No messages yet.</p>
      ) : (
        <div className="space-y-3">
          {items.map((m) => (
            <div
              key={m.id}
              className={`rounded-lg border p-4 ${
                m.is_read
                  ? "border-slate-200 bg-white"
                  : "border-amber-200 bg-amber-50"
              }`}
            >
              <div className="flex items-center justify-between gap-4">
                <p className="font-medium text-slate-900">
                  {m.caller_name ?? "Unknown caller"}
                </p>
                <span className="text-xs text-slate-500">
                  {new Date(m.captured_at).toLocaleString()}
                </span>
              </div>
              <p className="mt-1 text-sm text-slate-700">
                {m.caller_phone ?? "(no phone)"}
              </p>
              <p className="mt-2 text-slate-700">
                {m.message_reason ?? "(no reason given)"}
              </p>
              <div className="mt-3 flex items-center gap-3 text-xs text-slate-500">
                <span>Email: {m.email_sent ? "sent" : "not sent"}</span>
                {!m.is_read ? (
                  <button
                    onClick={() => markRead(m.id)}
                    className="text-slate-700 underline hover:text-slate-900"
                  >
                    Mark as read
                  </button>
                ) : (
                  <span className="text-slate-400">Read</span>
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
}
