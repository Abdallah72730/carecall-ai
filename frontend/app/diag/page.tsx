"use client";

import { useEffect, useState } from "react";

const DEFAULT_API_BASE = "https://backend-production-d0cf2.up.railway.app";
const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || DEFAULT_API_BASE;

export default function DiagPage() {
  const [healthStatus, setHealthStatus] = useState<string>("...");
  const [healthBody, setHealthBody] = useState<string>("");
  const [healthError, setHealthError] = useState<string>("");

  useEffect(() => {
    (async () => {
      try {
        const r = await fetch(`${API_BASE}/health`, { cache: "no-store" });
        setHealthStatus(`${r.status} ${r.statusText}`);
        setHealthBody(await r.text());
      } catch (e) {
        setHealthError((e as Error).message);
      }
    })();
  }, []);

  return (
    <main className="min-h-screen bg-slate-50 p-8">
      <div className="mx-auto max-w-2xl space-y-4 rounded-lg bg-white p-6 shadow-sm">
        <h1 className="text-xl font-bold text-slate-900">Frontend diagnostics</h1>
        <dl className="space-y-2 text-sm">
          <div>
            <dt className="font-semibold text-slate-500">
              process.env.NEXT_PUBLIC_API_BASE_URL
            </dt>
            <dd className="mt-1 break-all rounded border border-slate-200 bg-slate-50 p-2 font-mono">
              {process.env.NEXT_PUBLIC_API_BASE_URL || "(not set)"}
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-500">
              Resolved API_BASE used by the bundle
            </dt>
            <dd className="mt-1 break-all rounded border border-slate-200 bg-slate-50 p-2 font-mono">
              {API_BASE}
            </dd>
          </div>
          <div>
            <dt className="font-semibold text-slate-500">/health response</dt>
            <dd className="mt-1 rounded border border-slate-200 bg-slate-50 p-2 font-mono">
              <div>status: {healthStatus}</div>
              <div>body: {healthBody}</div>
              {healthError ? (
                <div className="text-red-700">error: {healthError}</div>
              ) : null}
            </dd>
          </div>
        </dl>
        <p className="text-xs text-slate-500">
          Build commit: {process.env.NEXT_PUBLIC_GIT_SHA || "(unset)"}
        </p>
      </div>
    </main>
  );
}
