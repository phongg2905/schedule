"use client";

import type { ReactNode } from "react";
import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import { NextIntlClientProvider } from "next-intl";

import enMessages from "../../messages/en.json";
import viMessages from "../../messages/vi.json";
import { fetchMe } from "@/services/auth";
import { fetchLanguagePreference, updateLanguagePreference, type Language } from "@/services/preferences";

const STORAGE_KEY = "ai-planner.locale";
const DEFAULT_LOCALE: Language = "en";
const DEFAULT_TIME_ZONE = "Asia/Ho_Chi_Minh";
const messages = {
  en: enMessages,
  vi: viMessages,
} as const;

type IntlContextValue = {
  locale: Language;
  isAuthenticated: boolean;
  clearSession: () => void;
  setLocale: (locale: Language) => Promise<void>;
  syncLocaleFromServer: () => Promise<void>;
  formatDate: (value: string | Date) => string;
  formatDateTime: (value: string | Date) => string;
};

const IntlContext = createContext<IntlContextValue | null>(null);

function readStoredLocale(): Language {
  if (typeof window === "undefined") {
    return DEFAULT_LOCALE;
  }

  const stored = window.localStorage.getItem(STORAGE_KEY);
  return stored === "vi" ? "vi" : "en";
}

function parseDateInput(value: string | Date): Date {
  if (value instanceof Date) {
    return value;
  }

  const normalized = value.length === 10 ? `${value}T00:00:00` : value;
  return new Date(normalized);
}

export function IntlProvider({ children }: Readonly<{ children: ReactNode }>) {
  const [locale, setLocaleState] = useState<Language>(DEFAULT_LOCALE);
  const [isAuthenticated, setIsAuthenticated] = useState(false);

  const persistLocale = useCallback((nextLocale: Language) => {
    setLocaleState(nextLocale);
    if (typeof document !== "undefined") {
      document.documentElement.lang = nextLocale;
    }
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, nextLocale);
    }
  }, []);

  const syncLocaleFromServer = useCallback(async () => {
    try {
      await fetchMe();
      setIsAuthenticated(true);
      const preference = await fetchLanguagePreference();
      persistLocale(preference.language === "vi" ? "vi" : "en");
    } catch {
      setIsAuthenticated(false);
    }
  }, [persistLocale]);

  const clearSession = useCallback(() => {
    setIsAuthenticated(false);
  }, []);

  const setLocale = useCallback(
    async (nextLocale: Language) => {
      if (isAuthenticated) {
        await updateLanguagePreference(nextLocale);
      }
      persistLocale(nextLocale);
    },
    [isAuthenticated, persistLocale]
  );

  useEffect(() => {
    persistLocale(readStoredLocale());
  }, [persistLocale]);

  useEffect(() => {
    void syncLocaleFromServer();
  }, [syncLocaleFromServer]);

  useEffect(() => {
    if (typeof document !== "undefined") {
      document.documentElement.lang = locale;
    }
  }, [locale]);

  const value = useMemo<IntlContextValue>(
    () => ({
      locale,
      isAuthenticated,
      clearSession,
      setLocale,
      syncLocaleFromServer,
      formatDate: (input) =>
        new Intl.DateTimeFormat(locale, {
          dateStyle: "medium",
        }).format(parseDateInput(input)),
      formatDateTime: (input) =>
        new Intl.DateTimeFormat(locale, {
          dateStyle: "medium",
          timeStyle: "short",
        }).format(parseDateInput(input)),
    }),
    [clearSession, isAuthenticated, locale, setLocale, syncLocaleFromServer]
  );

  return (
    <IntlContext.Provider value={value}>
      <NextIntlClientProvider locale={locale} messages={messages[locale]} timeZone={DEFAULT_TIME_ZONE}>
        {children}
      </NextIntlClientProvider>
    </IntlContext.Provider>
  );
}

export function useAppIntl() {
  const context = useContext(IntlContext);
  if (!context) {
    throw new Error("useAppIntl must be used within IntlProvider");
  }
  return context;
}
