import { createClient } from "@/lib/supabase/server";

function startOfDayUTC(d: Date) {
  const x = new Date(d);
  x.setUTCHours(0, 0, 0, 0);
  return x;
}

export default async function DashboardOverviewPage() {
  const supabase = await createClient();
  const today = startOfDayUTC(new Date()).toISOString();
  const weekAgo = new Date(Date.now() - 7 * 24 * 60 * 60 * 1000).toISOString();

  const [callsToday, callsWeek, messagesWeek, unreadMessages] = await Promise.all([
    supabase
      .from("call_logs")
      .select("id", { count: "exact", head: true })
      .gte("started_at", today),
    supabase
      .from("call_logs")
      .select("id", { count: "exact", head: true })
      .gte("started_at", weekAgo),
    supabase
      .from("after_hours_messages")
      .select("id", { count: "exact", head: true })
      .gte("captured_at", weekAgo),
    supabase
      .from("after_hours_messages")
      .select("id", { count: "exact", head: true })
      .eq("is_read", false),
  ]);

  const stats = [
    { label: "Calls today", value: callsToday.count ?? 0 },
    { label: "Calls (last 7 days)", value: callsWeek.count ?? 0 },
    { label: "Messages (last 7 days)", value: messagesWeek.count ?? 0 },
    { label: "Unread messages", value: unreadMessages.count ?? 0 },
  ];

  return (
    <section className="space-y-6">
      <h1 className="text-2xl font-bold text-slate-900">Overview</h1>
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-4">
        {stats.map((s) => (
          <div
            key={s.label}
            className="rounded-lg border border-slate-200 bg-white p-5"
          >
            <p className="text-sm text-slate-500">{s.label}</p>
            <p className="mt-2 text-3xl font-semibold text-slate-900">
              {s.value}
            </p>
          </div>
        ))}
      </div>
    </section>
  );
}
