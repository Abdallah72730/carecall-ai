"use client";

import Link from "next/link";
import { useState } from "react";
import { api } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

type Tier = {
  id: "pilot" | "starter";
  name: string;
  price: string;
  cadence: string;
  blurb: string;
  features: string[];
  priceEnv: "NEXT_PUBLIC_STRIPE_PILOT_PRICE_ID" | "NEXT_PUBLIC_STRIPE_STARTER_PRICE_ID";
  highlight?: boolean;
};

const TIERS: Tier[] = [
  {
    id: "pilot",
    name: "Pilot",
    price: "$99",
    cadence: "/month CAD",
    blurb: "For solo practices testing AI reception during pilot rollout.",
    features: [
      "24/7 AI voice receptionist",
      "Up to 200 calls/month",
      "After-hours message capture + email",
      "Knowledge base of up to 50 FAQs",
      "Email support",
    ],
    priceEnv: "NEXT_PUBLIC_STRIPE_PILOT_PRICE_ID",
  },
  {
    id: "starter",
    name: "Starter",
    price: "$149",
    cadence: "/month CAD",
    blurb: "For active clinics ready to use CareCall as primary reception.",
    features: [
      "Everything in Pilot",
      "Unlimited calls",
      "Unlimited FAQs",
      "Priority support",
      "Custom assistant voice + greeting",
    ],
    priceEnv: "NEXT_PUBLIC_STRIPE_STARTER_PRICE_ID",
    highlight: true,
  },
];

export default function PricingPage() {
  const [loading, setLoading] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function startCheckout(tier: Tier) {
    setError(null);
    const priceId = process.env[tier.priceEnv];
    if (!priceId) {
      setError(
        `Pricing not configured yet. ${tier.priceEnv} is missing on this deploy.`,
      );
      return;
    }
    setLoading(tier.id);
    try {
      const supabase = createClient();
      const {
        data: { session },
      } = await supabase.auth.getSession();
      if (!session) {
        window.location.href = `/login?redirect=/pricing`;
        return;
      }
      const { url } = await api<{ url: string }>("/billing/checkout", {
        method: "POST",
        body: JSON.stringify({ price_id: priceId }),
      });
      window.location.href = url;
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setLoading(null);
    }
  }

  return (
    <main className="min-h-screen bg-slate-50 px-6 py-16">
      <div className="mx-auto max-w-4xl space-y-10">
        <header className="text-center">
          <Link
            href="/"
            className="text-sm text-slate-500 hover:text-slate-700"
          >
            &larr; Home
          </Link>
          <h1 className="mt-3 text-3xl font-bold text-slate-900 sm:text-4xl">
            Pricing
          </h1>
          <p className="mt-3 text-slate-600">
            Simple, monthly. Cancel anytime.
          </p>
        </header>

        {error ? (
          <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            {error}
          </div>
        ) : null}

        <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
          {TIERS.map((t) => (
            <div
              key={t.id}
              className={`rounded-xl border bg-white p-6 ${
                t.highlight
                  ? "border-slate-900 shadow-md"
                  : "border-slate-200"
              }`}
            >
              <div className="flex items-baseline justify-between">
                <h2 className="text-xl font-bold text-slate-900">{t.name}</h2>
                {t.highlight ? (
                  <span className="rounded-full bg-slate-900 px-2.5 py-0.5 text-xs font-medium text-white">
                    Most chosen
                  </span>
                ) : null}
              </div>
              <p className="mt-2 text-sm text-slate-600">{t.blurb}</p>
              <p className="mt-5">
                <span className="text-4xl font-bold text-slate-900">
                  {t.price}
                </span>
                <span className="ml-1 text-slate-500">{t.cadence}</span>
              </p>
              <ul className="mt-5 space-y-2 text-sm text-slate-700">
                {t.features.map((f) => (
                  <li key={f} className="flex gap-2">
                    <span className="text-slate-400">•</span>
                    <span>{f}</span>
                  </li>
                ))}
              </ul>
              <button
                onClick={() => startCheckout(t)}
                disabled={loading === t.id}
                className={`mt-6 w-full rounded px-4 py-2.5 text-sm font-semibold transition disabled:opacity-50 ${
                  t.highlight
                    ? "bg-slate-900 text-white hover:bg-slate-800"
                    : "border border-slate-300 text-slate-900 hover:bg-slate-100"
                }`}
              >
                {loading === t.id ? "Starting checkout..." : `Choose ${t.name}`}
              </button>
            </div>
          ))}
        </div>

        <p className="text-center text-xs text-slate-400">
          Pilot pricing is locked for the first 6 months. Prices in CAD.
        </p>
      </div>
    </main>
  );
}
