"use client";

import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import type { ReactNode } from "react";
import { useTranslations } from "next-intl";
import { motion } from "@/lib/motion";

import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { cn } from "@/lib/cn";
import { apiFetch } from "@/services/api";
import { useAppIntl } from "@/providers/intl-provider";

type NavItemProps = {
  href: "/" | "/today" | "/tasks" | "/history" | "/settings" | "/profile";
  label: string;
  isActive: boolean;
  icon: ReactNode;
};

function NavItem({ href, label, isActive, icon }: Readonly<NavItemProps>) {
  return (
    <Link
      href={href}
      className={cn(
        "relative flex items-center gap-2.5 rounded-pill px-3 lg:px-4 py-2 text-sm font-medium transition-all duration-200",
        isActive
          ? "bg-coral-50 text-coral-600"
          : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700"
      )}
    >
      <span className="h-4 w-4">{icon}</span>
      <span className="hidden md:inline">{label}</span>
      {isActive ? (
        <motion.span
          className="absolute -bottom-px left-1/2 h-0.5 w-6 -translate-x-1/2 rounded-full bg-coral-400"
          layoutId="nav-active-indicator"
          transition={{ type: "spring", stiffness: 380, damping: 30 }}
        />
      ) : null}
    </Link>
  );
}

const mobileNavItems = [
  {
    href: "/" as const,
    labelKey: "home" as const,
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.6]">
        <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    ),
  },
  {
    href: "/today" as const,
    labelKey: "today" as const,
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.6]">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 3" />
      </svg>
    ),
  },
  {
    href: "/tasks" as const,
    labelKey: "tasks" as const,
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.6]">
        <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" />
        <rect x="9" y="3" width="6" height="4" rx="1" />
        <path d="M9 14l2 2 4-4" />
      </svg>
    ),
  },
  {
    href: "/history" as const,
    labelKey: "history" as const,
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.6]">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 3" />
        <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2" />
      </svg>
    ),
  },
  {
    href: "/settings" as const,
    labelKey: "settings" as const,
    icon: (
      <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.6]">
        <path d="M12.22 2h-.44a2 2 0 00-2 2v.18a2 2 0 01-1 1.73l-.43.25a2 2 0 01-2 0l-.15-.08a2 2 0 00-2.73.73l-.22.38a2 2 0 00.73 2.73l.15.1a2 2 0 011 1.72v.51a2 2 0 01-1 1.74l-.15.09a2 2 0 00-.73 2.73l.22.38a2 2 0 002.73.73l.15-.08a2 2 0 012 0l.43.25a2 2 0 011 1.73V20a2 2 0 002 2h.44a2 2 0 002-2v-.18a2 2 0 011-1.73l.43-.25a2 2 0 012 0l.15.08a2 2 0 002.73-.73l.22-.39a2 2 0 00-.73-2.73l-.15-.08a2 2 0 01-1-1.74v-.5a2 2 0 011-1.74l.15-.09a2 2 0 00.73-2.73l-.22-.38a2 2 0 00-2.73-.73l-.15.08a2 2 0 01-2 0l-.43-.25a2 2 0 01-1-1.73V4a2 2 0 00-2-2z" />
        <circle cx="12" cy="12" r="3" />
      </svg>
    ),
  },
];

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
    <div className="relative min-h-screen min-h-dvh w-full overflow-x-hidden bg-ambient">
      {/* Ambient background blobs - scaled down on mobile */}
      <div className="bg-blob bg-blob-1" aria-hidden="true" />
      <div className="bg-blob bg-blob-2" aria-hidden="true" />
      <div className="hidden sm:block bg-blob bg-blob-3" aria-hidden="true" />

      {/* Floating Navigation */}
      <header className="sticky top-0 z-30 sm:top-3 md:top-4 px-0 sm:px-4 md:px-6 lg:px-8">
        <div className="mx-auto w-full max-w-7xl">
          <motion.nav
            className={cn(
              "relative flex items-center justify-between",
              "rounded-none sm:rounded-[16px] md:rounded-[20px] border-0 sm:border border-white/80 bg-white/70 px-3 md:px-4 py-2 shadow-nav backdrop-blur-2xl",
              "transition-all duration-300"
            )}
            initial={{ y: -20, opacity: 0 }}
            animate={{ y: 0, opacity: 1 }}
            transition={{ duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
          >
            {/* Logo */}
            <Link
              href={isAuthenticated ? "/" : "/"}
              className="flex items-center gap-2 md:gap-3 shrink-0"
            >
              <span className="relative flex h-8 w-8 md:h-9 md:w-9 lg:h-10 lg:w-10 items-center justify-center rounded-[10px] md:rounded-[12px] lg:rounded-[14px] bg-gradient-coral shadow-[0_4px_12px_rgba(255,122,92,0.2)]">
                <svg
                  viewBox="0 0 24 24"
                  className="relative h-4 w-4 md:h-5 md:w-5 fill-white"
                  aria-hidden="true"
                >
                  <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
                </svg>
              </span>
              <div className="hidden md:block">
                <p className="text-[10px] lg:text-[11px] font-semibold uppercase tracking-[0.15em] lg:tracking-[0.2em] text-coral-500">
                  {tApp("name")}
                </p>
              </div>
            </Link>

            {/* Center Navigation */}
            <div className="hidden md:flex items-center gap-0.5 lg:gap-1">
              {isAuthenticated ? (
                <>
                  <NavItem href="/" label={tNav("home")} isActive={pathname === "/"} icon={
                    <svg viewBox="0 0 24 24" className="h-full w-full fill-none stroke-current stroke-[1.8]">
                      <path d="M3 9l9-7 9 7v11a2 2 0 01-2 2H5a2 2 0 01-2-2V9z" />
                      <polyline points="9 22 9 12 15 12 15 22" />
                    </svg>
                  } />
                  <NavItem href="/today" label={tNav("today")} isActive={pathname === "/today"} icon={
                    <svg viewBox="0 0 24 24" className="h-full w-full fill-none stroke-current stroke-[1.8]">
                      <circle cx="12" cy="12" r="9" />
                      <path d="M12 7v5l3 3" />
                    </svg>
                  } />
                  <NavItem href="/tasks" label={tNav("tasks")} isActive={pathname === "/tasks"} icon={
                    <svg viewBox="0 0 24 24" className="h-full w-full fill-none stroke-current stroke-[1.8]">
                      <path d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2" />
                      <rect x="9" y="3" width="6" height="4" rx="1" />
                      <path d="M9 14l2 2 4-4" />
                    </svg>
                  } />
                  <NavItem href="/history" label={tNav("history")} isActive={pathname === "/history"} icon={
                    <svg viewBox="0 0 24 24" className="h-full w-full fill-none stroke-current stroke-[1.8]">
                      <circle cx="12" cy="12" r="9" />
                      <path d="M12 7v5l3 3" />
                      <path d="M12 2v2M12 20v2M4.93 4.93l1.41 1.41M17.66 17.66l1.41 1.41M2 12h2M20 12h2" />
                      <path d="M12 6v6l4 2" strokeDasharray="2 2" />
                    </svg>
                  } />
                  <NavItem href="/settings" label={tNav("settings")} isActive={pathname === "/settings"} icon={
                    <svg viewBox="0 0 24 24" className="h-full w-full fill-none stroke-current stroke-[1.8]">
                      <path d="M12.22 2h-.44a2 2 0 00-2 2v.18a2 2 0 011-1.73l-.43.25a2 2 0 01-2 0l-.15-.08a2 2 0 00-2.73.73l-.22.38a2 2 0 00.73 2.73l.15.1a2 2 0 011 1.72v.51a2 2 0 01-1 1.74l-.15.09a2 2 0 00-.73 2.73l.22.38a2 2 0 002.73.73l.15-.08a2 2 0 012 0l.43.25a2 2 0 011 1.73V20a2 2 0 002 2h.44a2 2 0 002-2v-.18a2 2 0 011-1.73l.43-.25a2 2 0 012 0l.15.08a2 2 0 002.73-.73l.22-.39a2 2 0 00-.73-2.73l-.15-.08a2 2 0 01-1-1.74v-.5a2 2 0 011-1.74l.15-.09a2 2 0 00.73-2.73l-.22-.38a2 2 0 00-2.73-.73l-.15.08a2 2 0 01-2 0l-.43-.25a2 2 0 01-1-1.73V4a2 2 0 00-2-2z" />
                      <circle cx="12" cy="12" r="3" />
                    </svg>
                  } />
                </>
              ) : null}
            </div>

            {/* Right side */}
            <div className="flex items-center gap-1 md:gap-1.5 lg:gap-2 shrink-0">
              <LanguageSwitcher />

              {isAuthenticated ? (
                <div className="flex items-center gap-1 md:gap-1.5 lg:gap-2">
                  <Link
                    href="/profile"
                    className={cn(
                      "relative flex items-center gap-1.5 lg:gap-2 rounded-pill px-2 lg:px-3 py-2 text-sm font-medium transition-all duration-200",
                      pathname === "/profile"
                        ? "bg-coral-50 text-coral-600"
                        : "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700"
                    )}
                    aria-label={tNav("profile")}
                  >
                    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]">
                      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                    <span className="hidden lg:inline">{tNav("profile")}</span>
                  </Link>
                  <button
                    onClick={logout}
                    className="flex items-center gap-1.5 lg:gap-2 rounded-pill px-1.5 lg:px-3 py-2 text-sm font-medium text-neutral-500 transition-colors hover:bg-neutral-100 hover:text-neutral-700"
                    aria-label={tCommon("logout")}
                  >
                    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]">
                      <path d="M9 21H5a2 2 0 01-2-2V5a2 2 0 012-2h4" />
                      <polyline points="16 17 21 12 16 7" />
                      <line x1="21" y1="12" x2="9" y2="12" />
                    </svg>
                    <span className="hidden lg:inline">{tCommon("logout")}</span>
                  </button>
                </div>
              ) : (
                <div className="flex items-center gap-1.5 md:gap-2">
                  <Link href="/login" className="btn-base btn-ghost btn-sm">
                    {tNav("login")}
                  </Link>
                  <Link href="/register" className="btn-base btn-primary btn-sm">
                    {tNav("register")}
                  </Link>
                </div>
              )}
            </div>
          </motion.nav>
        </div>
      </header>

      {/* Page content with padding bottom for mobile nav */}
      <motion.div
        className="relative z-10 w-full pb-16 sm:pb-0"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
      >
        {children}
      </motion.div>

      {/* Mobile Bottom Navigation Bar */}
      {isAuthenticated ? (
        <motion.nav
          className="fixed bottom-0 left-0 right-0 z-50 border-t border-border-light/80 bg-white/95 backdrop-blur-2xl md:hidden safe-area-bottom"
          initial={{ y: 50 }}
          animate={{ y: 0 }}
          transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <div className="flex items-center justify-around px-1 py-0.5">
            {mobileNavItems.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={cn(
                    "relative flex flex-col items-center gap-0.5 rounded-[12px] px-2 py-1.5 transition-all duration-200 touch-target",
                    isActive
                      ? "text-coral-500"
                      : "text-neutral-400 hover:text-neutral-600"
                  )}
                >
                  {/* Active indicator dot */}
                  {isActive && (
                    <motion.span
                      className="absolute -top-0.5 left-1/2 h-0.5 w-5 -translate-x-1/2 rounded-full bg-coral-400"
                      layoutId="mobile-nav-indicator"
                      transition={{ type: "spring", stiffness: 500, damping: 35 }}
                    />
                  )}
                  <span className={cn(
                    "flex h-7 w-7 items-center justify-center",
                    isActive && "drop-shadow-[0_1px_3px_rgba(255,122,92,0.3)]"
                  )}>
                    {item.icon}
                  </span>
                  <span className={cn(
                    "text-[10px] font-medium leading-none",
                    isActive ? "text-coral-500" : "text-neutral-400"
                  )}>
                    {tNav(item.labelKey)}
                  </span>
                </Link>
              );
            })}
          </div>
          {/* Safe area spacer */}
          <div className="h-safe-area-bottom safe-area-bottom" />
        </motion.nav>
      ) : null}
    </div>
  );
}
