"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { motion } from "@/lib/motion";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { getErrorMessage } from "@/lib/api-error";
import { apiFetch } from "@/services/api";
import { FadeInUp, fadeInUp } from "@/lib/motion";

export default function RegisterPage() {
  const router = useRouter();
  const tRegister = useTranslations("auth.register");
  const tCommon = useTranslations("common");
  const tErrors = useTranslations("errors");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, name, password, timezone: "Asia/Saigon" }),
      });
      router.push("/login");
    } catch (err) {
      setError(getErrorMessage(err, tErrors));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen min-h-dvh w-full overflow-x-hidden bg-ambient">
      {/* Left - Brand & Illustration */}
      <motion.div
        className="relative hidden w-1/2 flex-col justify-between overflow-hidden bg-gradient-to-br from-sky-400 to-sky-300 p-8 xl:p-12 lg:flex"
        initial={{ opacity: 0, x: -60 }}
        animate={{ opacity: 1, x: 0 }}
        transition={{ duration: 0.7, ease: [0.25, 0.1, 0.25, 1] }}
      >
        <div className="pointer-events-none absolute -right-20 -top-20 h-72 sm:h-96 w-72 sm:w-96 rounded-full bg-white/10" />
        <div className="pointer-events-none absolute -bottom-32 -left-32 h-[400px] sm:h-[500px] w-[400px] sm:w-[500px] rounded-full bg-white/5" />
        <div className="pointer-events-none absolute left-1/4 top-1/3 h-32 sm:h-40 w-32 sm:w-40 rounded-full bg-white/8" />

        <motion.div
          className="relative"
          initial={{ opacity: 0, y: -20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.3, duration: 0.5 }}
        >
          <div className="flex items-center gap-3">
            <span className="flex h-10 sm:h-12 w-10 sm:w-12 items-center justify-center rounded-[12px] sm:rounded-[16px] bg-white/20 backdrop-blur-sm">
              <svg viewBox="0 0 24 24" className="h-5 w-5 sm:h-6 sm:w-6 fill-white">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
              </svg>
            </span>
            <span className="text-base sm:text-lg font-semibold tracking-tight text-white/90">AI Planner</span>
          </div>
        </motion.div>

        <motion.div
          className="relative space-y-3 sm:space-y-4"
          initial={{ opacity: 0, y: 30 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.5, duration: 0.6 }}
        >
          <h1 className="font-display text-2xl sm:text-3xl xl:text-4xl font-bold leading-tight text-white">
            {tRegister("brandTitle")}
            <br />
            {tRegister("brandSubtitle")}
          </h1>
          <p className="max-w-md text-sm sm:text-base leading-relaxed text-white/70">
            {tRegister("brandDescription")}
          </p>
        </motion.div>

        <motion.div
          className="relative"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.8, duration: 0.4 }}
        >
          <p className="text-xs sm:text-sm text-white/50">&copy; 2026 AI Planner &mdash; Your daily companion</p>
        </motion.div>
      </motion.div>

      {/* Right - Form */}
      <div className="flex w-full items-center justify-center px-4 sm:px-6 lg:w-1/2">
        <FadeInUp className="w-full max-w-sm">
          {/* Mobile brand */}
          <motion.div
            className="mb-8 text-center lg:hidden"
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4 }}
          >
            <span className="mx-auto mb-4 flex h-12 sm:h-14 w-12 sm:w-14 items-center justify-center rounded-[14px] sm:rounded-[18px] bg-gradient-coral shadow-button-primary">
              <svg viewBox="0 0 24 24" className="h-6 w-6 sm:h-7 sm:w-7 fill-white">
                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z" />
              </svg>
            </span>
            <h1 className="font-display text-xl sm:text-2xl font-semibold text-neutral-900">{tRegister("title")}</h1>
            <p className="mt-1 text-xs sm:text-sm text-neutral-500">{tRegister("subtitle")}</p>
          </motion.div>

          {/* Desktop heading */}
          <motion.div
            className="mb-8 hidden lg:block"
            variants={fadeInUp}
            initial="hidden"
            animate="visible"
            transition={{ delay: 0.2 }}
          >
            <p className="section-label text-sky-400">{tRegister("eyebrow")}</p>
            <h1 className="mt-2 font-display text-2xl sm:text-3xl font-semibold tracking-tight text-neutral-900">
              {tRegister("title")}
            </h1>
            <p className="mt-1 sm:mt-2 text-xs sm:text-sm text-neutral-500">{tRegister("subtitle")}</p>
          </motion.div>

          <motion.form
            onSubmit={onSubmit}
            className="space-y-4 sm:space-y-5"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3, duration: 0.5 }}
          >
            <div className="space-y-1.5">
              <label className="text-[11px] sm:text-xs font-medium text-neutral-600">{tRegister("name")}</label>
              <Input placeholder={tRegister("namePlaceholder")} value={name} onChange={(event) => setName(event.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <label className="text-[11px] sm:text-xs font-medium text-neutral-600">{tRegister("email")}</label>
              <Input type="email" placeholder="you@example.com" value={email} onChange={(event) => setEmail(event.target.value)} required />
            </div>
            <div className="space-y-1.5">
              <label className="text-[11px] sm:text-xs font-medium text-neutral-600">{tRegister("password")}</label>
              <Input type="password" placeholder={tRegister("passwordPlaceholder")} value={password} onChange={(event) => setPassword(event.target.value)} required />
            </div>

            {error ? (
              <motion.p
                className="rounded-soft border border-coral-100 bg-coral-50 px-3 sm:px-4 py-3 text-xs sm:text-sm text-coral-600"
                initial={{ opacity: 0, y: -10 }}
                animate={{ opacity: 1, y: 0 }}
              >
                {error}
              </motion.p>
            ) : null}

            <Button className="w-full" disabled={loading || !name || !email || !password} type="submit" size="lg">
              {loading ? tCommon("creating") : tCommon("createAccount")}
            </Button>

            <p className="text-center text-xs sm:text-sm text-neutral-500">
              {tRegister("hasAccount")}{" "}
              <Link href="/login" className="font-semibold text-coral-500 transition-colors hover:text-coral-600">
                {tRegister("signInLink")}
              </Link>
            </p>
          </motion.form>
        </FadeInUp>
      </div>
    </div>
  );
}
