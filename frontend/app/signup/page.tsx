"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useState } from "react";
import { createClient } from "@/lib/supabase/client";

export default function SignupPage() {
  const router = useRouter();
  const [clinicName, setClinicName] = useState("");
  const [email, setEmail] = useState("");
  const [phone, setPhone] = useState("");
  const [transferNumber, setTransferNumber] = useState("");
  const [enableTransfer, setEnableTransfer] = useState(false);
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [done, setDone] = useState(false);

  async function handleSubmit(event: React.FormEvent) {
    event.preventDefault();
    setError(null);

    if (password.length < 8) {
      setError("Password must be at least 8 characters.");
      return;
    }

    setLoading(true);
    try {
      const supabase = createClient();
      const cleanedTransfer = enableTransfer ? transferNumber.trim() : "";
      const { data, error: signupErr } = await supabase.auth.signUp({
        email,
        password,
        options: {
          data: {
            clinic_name: clinicName,
            clinic_phone: phone,
            clinic_transfer_number: cleanedTransfer,
          },
        },
      });
      if (signupErr) throw signupErr;

      // The clinic row is auto-created by an auth.users INSERT trigger
      // (migration 004). If email confirmation is on, session is null
      // and we'll show a check-your-inbox screen.
      if (!data.session) {
        setDone(true);
        return;
      }
      router.push("/dashboard");
      router.refresh();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(false);
    }
  }

  if (done) {
    return (
      <main className="flex min-h-screen items-center justify-center bg-slate-50 p-8">
        <div className="max-w-md rounded-lg bg-white p-8 shadow text-center">
          <h1 className="text-2xl font-bold text-slate-900">Check your inbox</h1>
          <p className="mt-3 text-slate-600">
            We sent a confirmation link to <strong>{email}</strong>. Click it to
            finish creating your CareCall AI account.
          </p>
          <p className="mt-6 text-sm text-slate-500">
            Already confirmed?{" "}
            <Link href="/login" className="text-slate-900 underline">
              Sign in
            </Link>
            .
          </p>
        </div>
      </main>
    );
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 p-8">
      <form
        onSubmit={handleSubmit}
        className="w-full max-w-md space-y-4 rounded-lg bg-white p-8 shadow"
      >
        <div>
          <h1 className="text-2xl font-bold text-slate-900">Start your pilot</h1>
          <p className="mt-1 text-sm text-slate-500">
            14-day trial. No credit card required.
          </p>
        </div>

        <div className="space-y-3">
          <input
            placeholder="Clinic name"
            value={clinicName}
            onChange={(e) => setClinicName(e.target.value)}
            required
            className="w-full rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-500"
          />
          <input
            type="email"
            placeholder="Work email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="w-full rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-500"
          />
          <input
            type="tel"
            placeholder="Clinic phone number (the public number patients dial)"
            value={phone}
            onChange={(e) => setPhone(e.target.value)}
            className="w-full rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-500"
          />

          <label className="flex items-start gap-2 pt-1 text-sm text-slate-700">
            <input
              type="checkbox"
              checked={enableTransfer}
              onChange={(e) => setEnableTransfer(e.target.checked)}
              className="mt-1"
            />
            <span>
              Forward calls to a human receptionist when the clinic is open.
              The AI handles after-hours calls either way.
            </span>
          </label>

          {enableTransfer ? (
            <input
              type="tel"
              placeholder="Receptionist forwarding number (e.g. +15875551234)"
              value={transferNumber}
              onChange={(e) => setTransferNumber(e.target.value)}
              required={enableTransfer}
              className="w-full rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-500"
            />
          ) : null}

          <input
            type="password"
            placeholder="Password (min 8 characters)"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            minLength={8}
            className="w-full rounded border border-slate-300 px-3 py-2 outline-none focus:border-slate-500"
          />
        </div>

        {error ? (
          <p className="text-sm text-red-600" role="alert">
            {error}
          </p>
        ) : null}

        <button
          type="submit"
          disabled={loading}
          className="w-full rounded bg-slate-900 px-4 py-2.5 font-semibold text-white transition hover:bg-slate-800 disabled:opacity-50"
        >
          {loading ? "Creating account..." : "Create account"}
        </button>

        <p className="text-center text-sm text-slate-500">
          Already have an account?{" "}
          <Link href="/login" className="text-slate-900 underline">
            Sign in
          </Link>
        </p>
      </form>
    </main>
  );
}
