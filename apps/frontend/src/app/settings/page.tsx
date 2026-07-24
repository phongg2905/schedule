"use client";

import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { motion, AnimatePresence } from "@/lib/motion";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import { SectionHeader } from "@/components/ui/section-header";
import { getErrorMessage } from "@/lib/api-error";
import { apiFetch } from "@/services/api";
import { fetchMe } from "@/services/auth";
import { LanguageSwitcher } from "@/components/layout/language-switcher";
import { cn } from "@/lib/cn";
import { FadeIn, FadeInDown } from "@/lib/motion";

type Preferences = {
  timezone: string;
  work_start_time: string;
  work_end_time: string;
  lunch_start_time: string;
  lunch_end_time: string;
  day_offs: string[];
  focus_hours: string[];
};

type UserProfile = {
  email: string;
  name: string;
  timezone: string;
};

const fallbackPreferences: Preferences = {
  timezone: "Asia/Saigon",
  work_start_time: "09:00",
  work_end_time: "17:00",
  lunch_start_time: "12:00",
  lunch_end_time: "13:00",
  day_offs: ["Sunday"],
  focus_hours: ["09:00-11:00", "14:00-16:00"],
};

type SectionCardProps = {
  icon: React.ReactNode;
  title: string;
  description: string;
  children: React.ReactNode;
  className?: string;
  index?: number;
};

function SectionCard({ icon, title, description, children, className, index = 0 }: Readonly<SectionCardProps>) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay: 0.2 + index * 0.1, duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <Card variant="glass" className={cn("overflow-hidden", className)}>
        <div className="p-6 sm:p-8">
          <div className="mb-6 flex items-start gap-4">
            <motion.div
              className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-coral-50 text-coral-500"
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              transition={{ delay: 0.3 + index * 0.1, duration: 0.4 }}
            >
              {icon}
            </motion.div>
            <div>
              <h2 className="font-display text-lg font-semibold text-neutral-900">{title}</h2>
              <p className="mt-0.5 text-sm text-neutral-500">{description}</p>
            </div>
          </div>
          {children}
        </div>
      </Card>
    </motion.div>
  );
}

export default function SettingsPage() {
  const router = useRouter();
  const tSettings = useTranslations("settings");
  const tErrors = useTranslations("errors");
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [timezone, setTimezone] = useState(fallbackPreferences.timezone);
  const [workStartTime, setWorkStartTime] = useState(fallbackPreferences.work_start_time);
  const [workEndTime, setWorkEndTime] = useState(fallbackPreferences.work_end_time);
  const [lunchStartTime, setLunchStartTime] = useState(fallbackPreferences.lunch_start_time);
  const [lunchEndTime, setLunchEndTime] = useState(fallbackPreferences.lunch_end_time);
  const [dayOffs, setDayOffs] = useState(fallbackPreferences.day_offs.join(", "));
  const [focusHours, setFocusHours] = useState(fallbackPreferences.focus_hours.join(", "));
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const [messageVariant, setMessageVariant] = useState<"success" | "error">("success");

  async function load() {
    try {
      const [me, preferences] = await Promise.all([fetchMe(), apiFetch<Preferences>("/settings/preferences")]);
      setProfile(me);
      setTimezone(preferences.timezone ?? me.timezone);
      setWorkStartTime(preferences.work_start_time);
      setWorkEndTime(preferences.work_end_time);
      setLunchStartTime(preferences.lunch_start_time);
      setLunchEndTime(preferences.lunch_end_time);
      setDayOffs(preferences.day_offs.join(", "));
      setFocusHours(preferences.focus_hours.join(", "));
    } catch { router.push("/login"); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      await apiFetch<Preferences>("/settings/preferences", {
        method: "PUT",
        body: JSON.stringify({
          timezone, work_start_time: workStartTime, work_end_time: workEndTime,
          lunch_start_time: lunchStartTime, lunch_end_time: lunchEndTime,
          day_offs: dayOffs.split(",").map((item) => item.trim()).filter(Boolean),
          focus_hours: focusHours.split(",").map((item) => item.trim()).filter(Boolean),
        }),
      });
      setMessage(tSettings("saved"));
      setMessageVariant("success");
    } catch (error) {
      setMessage(getErrorMessage(error, tErrors));
      setMessageVariant("error");
    } finally { setSaving(false); }
  }

  if (loading) {
    return (
      <main className="mx-auto w-full max-w-5xl px-4 py-5 sm:px-6 lg:px-8">
        <FadeIn className="space-y-5 sm:space-y-6">
          <LoadingState lines={1} variant="card" />
          <LoadingState lines={3} variant="card" />
        </FadeIn>
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-5xl px-4 py-5 sm:px-6 lg:px-8">
      <motion.div className="space-y-5 sm:space-y-6 lg:space-y-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
        {/* Header */}
        <div className="space-y-2">
          <FadeInDown>
            <p className="section-label text-coral-500">{tSettings("eyebrow")}</p>
          </FadeInDown>
          <motion.h1 className="page-title" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            {tSettings("title")}
          </motion.h1>
          <motion.p className="max-w-xl text-sm leading-6 text-neutral-500" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
            {tSettings("description")}
          </motion.p>
        </div>

        <div className="grid gap-6">
          {/* Language */}
          <SectionCard
            index={0}
            icon={<svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="9" /><path d="M3 12h18" /><path d="M12 3c3.5 3.7 3.5 14.3 0 18" /><path d="M12 3c-3.5 3.7-3.5 14.3 0 18" /></svg>}
            title={tSettings("language.title")}
            description={tSettings("language.description")}
          >
            <div className="w-full max-w-[200px]">
              <LanguageSwitcher />
            </div>
          </SectionCard>

          {/* Working Schedule */}
          <SectionCard
            index={1}
            icon={<svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8]"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></svg>}
            title={tSettings("schedule.title")}
            description={tSettings("schedule.description")}
          >
            <form onSubmit={submit} className="space-y-4 sm:space-y-5">
              <div className="grid gap-3 sm:gap-5 grid-cols-1 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="text-[11px] sm:text-xs font-medium text-neutral-600">{tSettings("schedule.timezone")}</label>
                  <Input value={timezone} onChange={(event) => setTimezone(event.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[11px] sm:text-xs font-medium text-neutral-600">{tSettings("schedule.dayOffs")}</label>
                  <Input value={dayOffs} onChange={(event) => setDayOffs(event.target.value)} placeholder={tSettings("schedule.dayOffsPlaceholder")} />
                </div>
              </div>
              <div className="grid gap-3 sm:gap-5 grid-cols-1 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="text-[11px] sm:text-xs font-medium text-neutral-600">{tSettings("schedule.workStart")}</label>
                  <Input type="time" value={workStartTime} onChange={(event) => setWorkStartTime(event.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[11px] sm:text-xs font-medium text-neutral-600">{tSettings("schedule.workEnd")}</label>
                  <Input type="time" value={workEndTime} onChange={(event) => setWorkEndTime(event.target.value)} />
                </div>
              </div>
              <div className="grid gap-3 sm:gap-5 grid-cols-1 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="text-[11px] sm:text-xs font-medium text-neutral-600">{tSettings("schedule.lunchStart")}</label>
                  <Input type="time" value={lunchStartTime} onChange={(event) => setLunchStartTime(event.target.value)} />
                </div>
                <div className="space-y-1.5">
                  <label className="text-[11px] sm:text-xs font-medium text-neutral-600">{tSettings("schedule.lunchEnd")}</label>
                  <Input type="time" value={lunchEndTime} onChange={(event) => setLunchEndTime(event.target.value)} />
                </div>
              </div>
              <div className="space-y-1.5">
                <label className="text-[11px] sm:text-xs font-medium text-neutral-600">{tSettings("schedule.focusHours")}</label>
                <Input value={focusHours} onChange={(event) => setFocusHours(event.target.value)} placeholder={tSettings("schedule.focusHoursPlaceholder")} />
              </div>
              <AnimatePresence>
                {message ? (
                  <motion.div className={cn("rounded-soft border px-3 sm:px-4 py-3 text-xs sm:text-sm", messageVariant === "success" ? "border-mint-100 bg-mint-50 text-mint-700" : "border-coral-100 bg-coral-50 text-coral-700")} initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                    {message}
                  </motion.div>
                ) : null}
              </AnimatePresence>
              <div className="flex items-center gap-3 pt-2">
                <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                  <Button disabled={saving} type="submit" size="lg">
                    {saving ? tSettings("schedule.saving") : tSettings("schedule.save")}
                  </Button>
                </motion.div>
                {saving ? (
                  <motion.span className="flex items-center gap-2 text-xs text-neutral-500" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                    <motion.span className="h-1.5 w-1.5 rounded-full bg-coral-400" animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.5, repeat: Infinity }} />
                    Saving...
                  </motion.span>
                ) : null}
              </div>
            </form>
          </SectionCard>

          {/* Account */}
          <SectionCard
            index={2}
            icon={<svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8]"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>}
            title={tSettings("account.title")}
            description={tSettings("account.description")}
          >
            {profile ? (
              <div className="grid gap-5 sm:grid-cols-2">
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-neutral-600">{tSettings("account.name")}</label>
                  <Input value={profile.name} readOnly />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-neutral-600">{tSettings("account.email")}</label>
                  <Input value={profile.email} readOnly />
                </div>
                <div className="space-y-1.5">
                  <label className="text-xs font-medium text-neutral-600">{tSettings("account.timezone")}</label>
                  <Input value={profile.timezone} readOnly />
                </div>
              </div>
            ) : null}
          </SectionCard>
        </div>
      </motion.div>
    </main>
  );
}
