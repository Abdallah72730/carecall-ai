import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center bg-slate-50 p-8">
      <div className="max-w-xl text-center">
        <h1 className="mb-4 text-4xl font-bold text-slate-900">CareCall AI</h1>
        <p className="text-lg text-slate-600">
          AI voice receptionist for dental and healthcare clinics in Alberta.
        </p>
        <div className="mt-8 flex items-center justify-center gap-3">
          <Link
            href="/login"
            className="rounded bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition hover:bg-slate-800"
          >
            Clinic sign in
          </Link>
          <Link
            href="/dashboard"
            className="rounded border border-slate-300 px-5 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-white"
          >
            Open dashboard
          </Link>
        </div>
        <p className="mt-8 text-sm text-slate-400">Coming soon to clinics across Alberta.</p>
      </div>
    </main>
  );
}
