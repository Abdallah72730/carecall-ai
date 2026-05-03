import { createClient } from "@/lib/supabase/server";

type CallLog = {
  id: string;
  vapi_call_id: string | null;
  started_at: string;
  ended_at: string | null;
  duration_seconds: number | null;
  was_after_hours: boolean;
  call_summary: string | null;
  caller_number: string | null;
};

function formatDuration(seconds: number | null) {
  if (seconds == null) return "—";
  const m = Math.floor(seconds / 60);
  const s = seconds % 60;
  return `${m}:${s.toString().padStart(2, "0")}`;
}

export default async function CallsPage() {
  const supabase = await createClient();
  const { data, error } = await supabase
    .from("call_logs")
    .select(
      "id,vapi_call_id,started_at,ended_at,duration_seconds,was_after_hours,call_summary,caller_number",
    )
    .order("started_at", { ascending: false })
    .limit(50);

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Call logs</h1>
      {error ? (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          {error.message}
        </div>
      ) : null}

      {!data || data.length === 0 ? (
        <p className="text-slate-500">No calls yet.</p>
      ) : (
        <div className="overflow-hidden rounded-lg border border-slate-200 bg-white">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 text-left text-slate-500">
              <tr>
                <th className="px-4 py-2 font-medium">Started</th>
                <th className="px-4 py-2 font-medium">Caller</th>
                <th className="px-4 py-2 font-medium">Duration</th>
                <th className="px-4 py-2 font-medium">After hours</th>
                <th className="px-4 py-2 font-medium">Summary</th>
              </tr>
            </thead>
            <tbody>
              {(data as CallLog[]).map((c) => (
                <tr key={c.id} className="border-t border-slate-100">
                  <td className="px-4 py-3 align-top text-slate-700">
                    {new Date(c.started_at).toLocaleString()}
                  </td>
                  <td className="px-4 py-3 align-top text-slate-700">
                    {c.caller_number ?? "—"}
                  </td>
                  <td className="px-4 py-3 align-top text-slate-700">
                    {formatDuration(c.duration_seconds)}
                  </td>
                  <td className="px-4 py-3 align-top text-slate-700">
                    {c.was_after_hours ? "Yes" : "No"}
                  </td>
                  <td className="px-4 py-3 align-top text-slate-600">
                    {c.call_summary ?? "—"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </section>
  );
}
