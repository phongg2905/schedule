"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";

import { apiFetch } from "@/services/api";

export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname();
  const router = useRouter();

  async function logout() {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } finally {
      router.push("/login");
    }
  }

  return (
    <div>
      <header className="sticky top-0 z-20 border-b border-black/5 bg-[rgba(247,247,242,0.7)] backdrop-blur">
        <div className="mx-auto flex max-w-6xl items-center justify-between px-6 py-4">
          <Link href="/" className="text-sm font-semibold uppercase tracking-[0.22em] text-ink-800">
            AI Planner
          </Link>
          <nav className="flex items-center gap-3 text-sm text-slate-600">
            <Link className={pathname === "/today" ? "font-semibold text-ink-900" : ""} href="/today">
              Today
            </Link>
            <Link className={pathname === "/tasks" ? "font-semibold text-ink-900" : ""} href="/tasks">
              Tasks
            </Link>
            <Link className={pathname === "/settings" ? "font-semibold text-ink-900" : ""} href="/settings">
              Settings
            </Link>
            <Link href="/register">Register</Link>
            <Link href="/login">Login</Link>
            <button onClick={logout} className="rounded-full border border-black/10 px-3 py-1.5 text-xs font-medium text-ink-900">
              Logout
            </button>
          </nav>
        </div>
      </header>
      {children}
    </div>
  );
}
