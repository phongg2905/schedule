"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";

import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { cn } from "@/lib/cn";
import { apiFetch } from "@/services/api";
import { useAppIntl } from "@/providers/intl-provider";

type NavItemProps = {
  href: "/" | "/today" | "/tasks" | "/settings" | "/profile";
  label: string;
  isActive: boolean;
  icon: ReactNode;
};

function NavItem({ href, label, isActive, icon }: Readonly<NavItemProps>) {
  return (
    <Link
      href={href}
      className={cn(
        "relative flex items-center gap-2.5 rounded-pill px-4 py-2 text-sm font-medium transition-all duration-200",
        isActive
          ? "bg-coral-50 text-coral-600"
          : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700"
      )}
    >
      <span className="h-4 w-4">{icon}</span>
      <span className="hidden sm:inline">{label}</span>
      {isActive ? (
        <span className="absolute -bottom-px left-1/2 h-0.5 w-6 -translate-x-1/2 rounded-full bg-coral-400 opacity-0" />
      ) : null}
    </Link>
  );
}

export function AppShell({ children }: Readonly<{ children: ReactNode }>) {
  const pathname = usePathname();
  const router = useRouter();
  const { isAuthenticated, clearSession } = useAppIntl();
  const tApp = useTranslations("app");
  const tNav = useTranslations("nav");
  const tCommon = useTranslations("common");

  async function logout() {
    try {
      await apiFetch("/auth/logout", { method: "POST" });
    } finally {
      clearSession();
      router.push("/login");
    }
  }

  // Don't show the shell on auth pages
  const isAuthPage = pathname === "/login" || pathname === "/register";

  if (isAuthPage) {
    return <>{children}</>;
  }

  return (
    <div className="relative min-h-screen w-full overflow-x-hidden bg-ambient">
      {/* Ambient background blobs */}
      <div className="bg-blob bg-blob-1" aria-hidden="true" />
      <div className="bg-blob bg-blob-2" aria-hidden="true" />
      <div className="bg-blob bg-blob-3" aria-hidden="true" />

      {/* Floating Navigation */}
      <header className="sticky top-4 z-30 px-4 sm:px-6 lg:px-8">
        <div className="mx-auto max-w-7xl">
          <nav
            className={cn(
              "relative flex items-center justify-between",
              "rounded-[20px] border border-white/80 bg-white/70 px-4 py-2.5 shadow-nav backdrop-blur-2xl",
              "transition-all duration-300"
            )}
          >
            {/* Logo */}
            <Link
              href={isAuthenticated ? "/" : "/"}
              className="flex items-center gap-3"
            >
              <span className="relative flex h-10 w-10 items-center justify-center rounded-[14px] bg-gradient-coral shadow-[0_4px_12px_rgba(255,122,92,0.2)]">
                <svg
                  viewBox="0 0 24 24"
                  className="relative h-5 w-5 fill-white"
                  aria-hidden="true"
                >
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
                </svg>
              </span>
              <div className="hidden sm:block">
                <p className="text-[11px] font-semibold uppercase tracking-[0.2em] text-coral-500">
                  {tApp("name")}
                </p>
              </div>
            </Link>

            {/* Center Navigation */}
            <div className="flex items-center gap-1">
              {isAuthenticated ? (
                <>
                  <NavItem
                    href="/"
                    label={tNav("home")}
                    isActive={pathname === "/"}
                    icon={
                      <svg viewBox="0 0 24 24" className="h-full w-full fill-none stroke-current stroke-[1.8]">
                        <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                        <polyline points="9 22 9 12 15 12 15 22" />
                      </svg>
                    }
                  />
                  <NavItem
                    href="/today"
                    label={tNav("today")}
                    isActive={pathname === "/today"}
                    icon={
                      <svg viewBox="0 0 24 24" className="h-full w-full fill-none stroke-current stroke-[1.8]">
                        <circle cx="12" cy="12" r="9" />
                        <path d="M12 7v5l3 3" />
                      </svg>
                    }
                  />
                  <NavItem
                    href="/tasks"
                    label={tNav("tasks")}
                    isActive={pathname === "/tasks"}
                    icon={
                      <svg viewBox="0 0 24 24" className="h-full w-full fill-none stroke-current stroke-[1.8]">
                        <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" />
                        <rect x="9" y="3" width="6" height="4" rx="1" />
                        <path d="M9 14l2 2 4-4" />
                      </svg>
                    }
                  />
                  <NavItem
                    href="/settings"
                    label={tNav("settings")}
                    isActive={pathname === "/settings"}
                    icon={
                      <svg viewBox="0 0 24 24" className="h-full w-full fill-none stroke-current stroke-[1.8]">
                        <path d="M12.22 2h-.44a2 2 0 00-2 2v.18a2 2 0 01-1 1.73l-.43.25a2 2 0 01-2 0l-.15-.08a2 2 0 00-2.73.73l-.22.38a2 2 0 00.73 2.73l.15.1a2 2 0 011 1.72v.51a2 2 0 01-1 1.74l-.15.09a2 2 0 00-.73 2.73l.22.38a2 2 0 002.73.73l.15-.08a2 2 0 012 0l.43.25a2 2 0 011 1.73V20a2 2 0 002 2h.44a2 2 0 002-2v-.18a2 2 0 011-1.73l.43-.25a2 2 0 012 0l.15.08a2 2 0 002.73-.73l.22-.39a2 2 0 00-.73-2.73l-.15-.08a2 2 0 01-1-1.74v-.5a2 2 0 011-1.74l.15-.09a2 2 0 00.73-2.73l-.22-.38a2 2 0 00-2.73-.73l-.15.08a2 2 0 01-2 0l-.43-.25a2 2 0 01-1-1.73V4a2 2 0 00-2-2z" />
                        <circle cx="12" cy="12" r="3" />
                      </svg>
                    }
                  />
                </>
              ) : null}
            </div>

            {/* Right side */}
            <div className="flex items-center gap-2">
              <LanguageSwitcher />

              {isAuthenticated ? (
                <div className="flex items-center gap-2">
                  <Link
                    href="/profile"
                    className={cn(
                      "relative flex items-center gap-2 rounded-pill px-3 py-2 text-sm font-medium transition-all duration-200",
                      pathname === "/profile"
                        ? "bg-coral-50 text-coral-600"
                        : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700"
                    )}
                  >
                    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]">
                      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                    <span className="hidden sm:inline">{tNav("profile")}</span>
                  </Link>
                  <button
                    onClick={logout}
                    className="flex items-center gap-2 rounded-pill px-3 py-1.5 text-sm font-medium text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
                  >
                    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]">
                      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
                      <polyline points="16 17 21 12 16 7" />
                      <line x1="21" y1="12" x2="9" y2="12" />
                    </svg>
                    <span className="hidden sm:inline">{tCommon("logout")}</span>
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-2">
                  <Link
                    href="/login"
                    className="btn-base btn-ghost btn-sm"
                  >
                    {tNav("login")}
                  </Link>
                  <Link
                    href="/register"
                    className="btn-base btn-primary btn-sm"
                  >
                    {tNav("register")}
                  </Link>
                </div>
              )}
            </div>
          </nav>
        </div>
      </header>

      {/* Page content with entrance animation */}
      <motion.div
        className="relative z-10 w-full"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
      >
        {children}
      </motion.div>
    </div>
  );
}
