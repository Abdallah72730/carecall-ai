"use client";

import { useEffect, useState } from "react";
import { createClient } from "@/lib/supabase/client";

const DAY_LABELS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"];

type HoursRow = {
  id?: string;
  clinic_id?: string;
  day_of_week: number;
  open_time: string | null;
  close_time: string | null;
  is_closed: boolean;
  timezone: string;
};

function blankRow(dow: number): HoursRow {
  return {
    day_of_week: dow,
    open_time: "08:00",
    close_time: "17:00",
    is_closed: dow === 5 || dow === 6,
    timezone: "America/Edmonton",
  };
}

export default function HoursPage() {
  const [rows, setRows] = useState<HoursRow[]>(
    [0, 1, 2, 3, 4, 5, 6].map(blankRow),
  );
  const [clinicId, setClinicId] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function load() {
      const supabase = createClient();
      const { data: clinic } = await supabase
        .from("clinics")
        .select("id")
        .limit(1)
        .single();
      if (!clinic) {
        setError("No clinic linked to your account.");
        setLoading(false);
        return;
      }
      setClinicId(clinic.id);
      const { data } = await supabase
        .from("clinic_hours")
        .select("id,day_of_week,open_time,close_time,is_closed,timezone")
        .eq("clinic_id", clinic.id);
      const map = new Map<number, HoursRow>();
      (data || []).forEach((r) => map.set(r.day_of_week, r as HoursRow));
      const merged = [0, 1, 2, 3, 4, 5, 6].map(
        (dow) => map.get(dow) ?? blankRow(dow),
      );
      setRows(merged);
      setLoading(false);
    }
    load();
  }, []);

  function update(dow: number, patch: Partial<HoursRow>) {
    setRows((prev) =>
      prev.map((r) => (r.day_of_week === dow ? { ...r, ...patch } : r)),
    );
  }

  async function save() {
    if (!clinicId) return;
    setSaving(true);
    setError(null);
    setMessage(null);
    try {
      const supabase = createClient();
      const payload = rows.map((r) => ({
        clinic_id: clinicId,
        day_of_week: r.day_of_week,
        open_time: r.is_closed ? null : r.open_time,
        close_time: r.is_closed ? null : r.close_time,
        is_closed: r.is_closed,
        timezone: r.timezone,
      }));
      const { error: upsertErr } = await supabase
        .from("clinic_hours")
        .upsert(payload, { onConflict: "clinic_id,day_of_week" });
      if (upsertErr) throw upsertErr;
      setMessage("Hours saved.");
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Hours</h1>
      {error ? (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error}
        </div>
      ) : null}
      {message ? (
        <div className="rounded border border-emerald-200 bg-emerald-50 p-3 text-sm text-emerald-700">
          {message}
        </div>
      ) : null}

      {loading ? (
        <p className="text-slate-500">Loading...</p>
      ) : (
        <div className="space-y-2 rounded-lg border border-slate-200 bg-white p-5">
          {rows.map((row) => (
            <div
              key={row.day_of_week}
              className="flex items-center gap-4 border-b border-slate-100 py-2 last:border-b-0"
            >
              <div className="w-12 text-sm font-medium text-slate-700">
                {DAY_LABELS[row.day_of_week]}
              </div>
              <label className="flex items-center gap-2 text-sm text-slate-600">
                <input
                  type="checkbox"
                  checked={row.is_closed}
                  onChange={(e) =>
                    update(row.day_of_week, { is_closed: e.target.checked })
                  }
                />
                Closed
              </label>
              <input
                type="time"
                disabled={row.is_closed}
                value={row.open_time?.slice(0, 5) ?? ""}
                onChange={(e) =>
                  update(row.day_of_week, { open_time: e.target.value })
                }
                className="rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-50"
              />
              <span className="text-slate-400">to</span>
              <input
                type="time"
                disabled={row.is_closed}
                value={row.close_time?.slice(0, 5) ?? ""}
                onChange={(e) =>
                  update(row.day_of_week, { close_time: e.target.value })
                }
                className="rounded border border-slate-300 px-2 py-1 text-sm disabled:opacity-50"
              />
            </div>
          ))}
          <button
            onClick={save}
            disabled={saving}
            className="mt-3 rounded bg-slate-900 px-4 py-2 text-sm font-semibold text-white disabled:opacity-50"
          >
            {saving ? "Saving..." : "Save hours"}
          </button>
        </div>
      )}
    </section>
  );
}
