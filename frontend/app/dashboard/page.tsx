import { redirect } from "next/navigation";
import { createClient } from "@/lib/supabase/server";

export default async function DashboardPage() {
  const supabase = await createClient();
  const {
    data: { user },
  } = await supabase.auth.getUser();
  if (!user) redirect("/login");

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-3xl space-y-6">
        <header className="flex items-center justify-between">
          <h1 className="text-2xl font-bold text-slate-900">Dashboard</h1>
          <p className="text-sm text-slate-500">{user.email}</p>
        </header>
        <section className="rounded-lg bg-white p-6 shadow-sm">
          <h2 className="text-lg font-semibold text-slate-900">
            You are signed in.
          </h2>
          <p className="mt-2 text-slate-600">
            The full clinic admin portal — FAQs, hours, call logs, messages —
            arrives in M7. For now, this is a placeholder.
          </p>
        </section>
      </div>
    </main>
  );
}
