"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
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
          return (
            <Link
              key={item.href}
              href={item.href}
              className={`block rounded px-3 py-2 text-sm transition ${
                active
                  ? "bg-slate-900 text-white"
                  : "text-slate-700 hover:bg-slate-100"
              }`}
            >
              {item.label}
            </Link>
          );
        })}
      </nav>
      <div className="border-t border-slate-200 px-4 py-4 text-sm">
        {userEmail ? (
          <p className="truncate text-slate-500" title={userEmail}>
            {userEmail}
          </p>
        ) : null}
        <button
          onClick={signOut}
          className="mt-2 text-slate-700 underline-offset-2 hover:text-slate-900 hover:underline"
        >
          Sign out
        </button>
      </div>
    </aside>
  );
}
