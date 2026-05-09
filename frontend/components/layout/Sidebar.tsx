"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { createClient } from "@/lib/supabase/client";

const NAV = [
  { href: "/dashboard", label: "Overview" },
  { href: "/dashboard/faqs", label: "FAQs" },
  { href: "/dashboard/hours", label: "Hours" },
  { href: "/dashboard/calls", label: "Calls" },
  { href: "/dashboard/messages", label: "Messages" },
];

export function Sidebar({ userEmail }: { userEmail?: string | null }) {
  const pathname = usePathname();
  const router = useRouter();
  const [unread, setUnread] = useState<number>(0);

  useEffect(() => {
    const supabase = createClient();
    let cancelled = false;
    async function tick() {
      const { count } = await supabase
        .from("after_hours_messages")
        .select("id", { count: "exact", head: true })
        .eq("is_read", false);
      if (!cancelled) setUnread(count ?? 0);
    }
    tick();
    const id = setInterval(tick, 30_000);
    const onFocus = () => tick();
    window.addEventListener("focus", onFocus);
    return () => {
      cancelled = true;
      clearInterval(id);
      window.removeEventListener("focus", onFocus);
    };
  }, [pathname]);

  async function signOut() {
    const supabase = createClient();
    await supabase.auth.signOut();
    router.push("/login");
    router.refresh();
  }

  return (
    <aside className="flex w-56 flex-col border-r border-slate-200 bg-white">
      <div className="px-6 py-5">
        <Link href="/dashboard" className="text-lg font-bold text-slate-900">
          CareCall AI
        </Link>
      </div>
      <nav className="flex-1 space-y-1 px-3">
        {NAV.map((item) => {
          const active =
            pathname === item.href ||
            (item.href !== "/dashboard" && pathname.startsWith(item.href));
          const showBadge =
            item.href === "/dashboard/messages" && unread > 0;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`flex items-center justify-between rounded px-3 py-2 text-sm transition ${
                active
                  ? "bg-slate-900 text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              <span>{item.label}</span>
              {showBadge ? (
                <span
                  className={`ml-2 inline-flex min-w-[20px] items-center justify-center rounded-full px-2 py-0.5 text-xs font-semibold ${
                    active ? "bg-white text-slate-900" : "bg-amber-500 text-white"
                  }`}
                >
                  {unread}
                </span>
              ) : null}
            </Link>
          );
        })}
      </nav>
      <div className="space-y-2 border-t border-slate-200 px-4 py-4 text-sm">
        {userEmail ? (
          <p className="truncate text-slate-500" title={userEmail}>
            {userEmail}
          </p>
        ) : null}
        <BillingPortalLink />
        <Link
          href="/pricing"
          className="block text-slate-700 underline-offset-2 hover:text-slate-900 hover:underline"
        >
          Plans
        </Link>
        <button
          onClick={signOut}
          className="block text-slate-700 underline-offset-2 hover:text-slate-900 hover:underline"
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}

function BillingPortalLink() {
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function open() {
    setError(null);
    setLoading(true);
    try {
      const { url } = await api<{ url: string }>("/billing/portal", {
        method: "POST",
      });
      window.location.href = url;
    } catch (e) {
      setError((e as Error).message);
      setLoading(false);
    }
  }

  return (
    <div>
      <button
        onClick={open}
        disabled={loading}
        className="block text-slate-700 underline-offset-2 hover:text-slate-900 hover:underline disabled:opacity-50"
      >
        {loading ? "Opening..." : "Manage billing"}
      </button>
      {error ? (
        <p className="mt-1 text-xs text-red-600" title={error}>
          {error.length > 80 ? error.slice(0, 80) + "…" : error}
        </p>
      ) : null}
    </div>
  );
}
