import Link from "next/link";

const FEATURES = [
  {
    title: "Answers 24/7",
    body: "Calls go straight to the AI when your front desk is closed, in lunch breaks, or just busy.",
  },
  {
    title: "Trained on your clinic",
    body: "Hours, services, pricing, insurance — anything in your knowledge base, the assistant knows.",
  },
  {
    title: "Captures every after-hours message",
    body: "Caller name, phone, and reason are emailed to your clinic and posted to your dashboard the moment they hang up.",
  },
  {
    title: "No PHI stored",
    body: "Symptoms, diagnoses, and medications are explicitly off-limits. Built to fit Alberta privacy expectations.",
  },
  {
    title: "Hands-off setup",
    body: "We provision your assistant, plug in your numbers, and load your FAQs. You log in to make edits anytime.",
  },
  {
    title: "Cancel anytime",
    body: "Month-to-month, no contracts. Pause when you don't need it.",
  },
];

export default function Home() {
  return (
    <main className="min-h-screen bg-slate-50">
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-lg font-bold text-slate-900">
            CareCall AI
          </Link>
          <nav className="flex items-center gap-5 text-sm">
            <Link href="/pricing" className="text-slate-600 hover:text-slate-900">
              Pricing
            </Link>
            <Link href="/login" className="text-slate-600 hover:text-slate-900">
              Sign in
            </Link>
            <Link
              href="/signup"
              className="rounded bg-slate-900 px-4 py-2 font-semibold text-white hover:bg-slate-800"
            >
              Get started
            </Link>
          </nav>
        </div>
      </header>

      <section className="px-6 py-20">
        <div className="mx-auto max-w-3xl text-center">
          <h1 className="text-4xl font-bold tracking-tight text-slate-900 sm:text-5xl">
            An AI receptionist that never misses a call.
          </h1>
          <p className="mt-5 text-lg text-slate-600">
            CareCall AI answers your dental or healthcare clinic&apos;s phone 24/7,
            answers patient questions from your knowledge base, and captures
            after-hours messages so nothing falls through the cracks.
          </p>
          <div className="mt-8 flex items-center justify-center gap-3">
            <Link
              href="/signup"
              className="rounded bg-slate-900 px-6 py-3 text-sm font-semibold text-white hover:bg-slate-800"
            >
              Start a 14-day pilot
            </Link>
            <Link
              href="/pricing"
              className="rounded border border-slate-300 px-6 py-3 text-sm font-semibold text-slate-700 hover:bg-white"
            >
              See pricing
            </Link>
          </div>
          <p className="mt-4 text-xs text-slate-500">
            No credit card required to start. Built for clinics in Alberta.
          </p>
        </div>
      </section>

      <section className="px-6 pb-20">
        <div className="mx-auto grid max-w-5xl grid-cols-1 gap-6 sm:grid-cols-2 lg:grid-cols-3">
          {FEATURES.map((f) => (
            <div
              key={f.title}
              className="rounded-lg border border-slate-200 bg-white p-6"
            >
              <h3 className="text-base font-semibold text-slate-900">
                {f.title}
              </h3>
              <p className="mt-2 text-sm text-slate-600">{f.body}</p>
            </div>
          ))}
        </div>
      </section>

      <footer className="border-t border-slate-200 bg-white">
        <div className="mx-auto flex max-w-5xl flex-col items-center justify-between gap-3 px-6 py-6 text-sm text-slate-500 sm:flex-row">
          <p>&copy; {new Date().getFullYear()} CareCall AI</p>
          <div className="flex gap-5">
            <Link href="/pricing" className="hover:text-slate-700">
              Pricing
            </Link>
            <Link href="/login" className="hover:text-slate-700">
              Sign in
            </Link>
          </div>
        </div>
      </footer>
    </main>
  );
}
