"use client";

import { useState } from "react";
import { useTranslations } from "next-intl";

import { useAppIntl } from "@/providers/intl-provider";
import type { Language } from "@/services/preferences";
import { cn } from "@/lib/cn";

export function LanguageSwitcher() {
  const tLanguage = useTranslations("language");
  const { locale, setLocale } = useAppIntl();
  const [pending, setPending] = useState(false);

  async function changeLanguage(nextLocale: Language) {
    if (nextLocale === locale) return;
    setPending(true);
    try {
      await setLocale(nextLocale);
    } finally {
      setPending(false);
    }
  }

  return (
    <div className="relative">
      <select
        aria-label={tLanguage("switcherLabel")}
        className={cn(
          "h-9 cursor-pointer appearance-none rounded-pill border border-border-light bg-white/80 px-3 pr-8",
          "text-xs font-semibold text-neutral-600 outline-none",
          "transition-all duration-200 hover:border-neutral-300 hover:bg-white",
          "focus-visible:shadow-[0_0_0_3px_rgba(255,122,92,0.12)]",
          pending && "opacity-50"
        )}
        disabled={pending}
        value={locale}
        onChange={(event) => void changeLanguage(event.target.value as Language)}
      >
        <option value="en">{tLanguage("en")}</option>
        <option value="vi">{tLanguage("vi")}</option>
      </select>
      <span className="pointer-events-none absolute right-3 top-1/2 -translate-y-1/2 text-neutral-400">
        <svg viewBox="0 0 12 8" className="h-2 w-3 fill-none stroke-current stroke-[1.5]">
          <path d="M1 1l5 5 5-5" strokeLinecap="round" strokeLinejoin="round" />
        </svg>
      </span>
    </div>
  );
}
