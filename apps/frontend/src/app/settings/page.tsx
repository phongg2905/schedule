"use client";

import type { FormEvent } from "react";
import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/services/api";
import { fetchMe } from "@/services/auth";

type Preferences = {
  timezone: string;
  work_start_time: string;
  work_end_time: string;
  lunch_start_time: string;
  lunch_end_time: string;
  day_offs: string[];
  focus_hours: string[];
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

export default function SettingsPage() {
  const router = useRouter();
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

  async function load() {
    try {
      const [profile, preferences] = await Promise.all([
        fetchMe(),
        apiFetch<Preferences>("/settings/preferences"),
      ]);
      setTimezone(preferences.timezone ?? profile.timezone);
      setWorkStartTime(preferences.work_start_time);
      setWorkEndTime(preferences.work_end_time);
      setLunchStartTime(preferences.lunch_start_time);
      setLunchEndTime(preferences.lunch_end_time);
      setDayOffs(preferences.day_offs.join(", "));
      setFocusHours(preferences.focus_hours.join(", "));
    } catch {
      router.push("/login");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setSaving(true);
    setMessage(null);
    try {
      await apiFetch<Preferences>("/settings/preferences", {
        method: "PUT",
        body: JSON.stringify({
          timezone,
          work_start_time: workStartTime,
          work_end_time: workEndTime,
          lunch_start_time: lunchStartTime,
          lunch_end_time: lunchEndTime,
          day_offs: dayOffs
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
          focus_hours: focusHours
            .split(",")
            .map((item) => item.trim())
            .filter(Boolean),
        }),
      });
      setMessage("Preferences saved.");
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Unable to save preferences");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-3xl px-6 py-10">
      <section className="rounded-[28px] border border-[var(--border)] bg-[var(--surface)] p-8 shadow-soft backdrop-blur">
        <div className="space-y-2">
          <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Settings</p>
          <h1 className="text-3xl font-semibold tracking-tight text-ink-900">Working schedule & preferences</h1>
          <p className="text-sm text-slate-600">These settings feed the rule-based planner before AI enters the loop.</p>
        </div>
        {loading ? <p className="mt-6 text-slate-600">Loading...</p> : null}
        {!loading ? (
          <form onSubmit={submit} className="mt-6 space-y-4">
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-2 text-sm text-slate-700">
                <span>Timezone</span>
                <input className="w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3" value={timezone} onChange={(event) => setTimezone(event.target.value)} />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span>Day offs</span>
                <input className="w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3" value={dayOffs} onChange={(event) => setDayOffs(event.target.value)} placeholder="Sunday, Saturday" />
              </label>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-2 text-sm text-slate-700">
                <span>Working start</span>
                <input className="w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3" type="time" value={workStartTime} onChange={(event) => setWorkStartTime(event.target.value)} />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span>Working end</span>
                <input className="w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3" type="time" value={workEndTime} onChange={(event) => setWorkEndTime(event.target.value)} />
              </label>
            </div>
            <div className="grid gap-4 sm:grid-cols-2">
              <label className="space-y-2 text-sm text-slate-700">
                <span>Lunch start</span>
                <input className="w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3" type="time" value={lunchStartTime} onChange={(event) => setLunchStartTime(event.target.value)} />
              </label>
              <label className="space-y-2 text-sm text-slate-700">
                <span>Lunch end</span>
                <input className="w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3" type="time" value={lunchEndTime} onChange={(event) => setLunchEndTime(event.target.value)} />
              </label>
            </div>
            <label className="block space-y-2 text-sm text-slate-700">
              <span>Focus hours</span>
              <input className="w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3" value={focusHours} onChange={(event) => setFocusHours(event.target.value)} placeholder="09:00-11:00, 14:00-16:00" />
            </label>
            {message ? <p className="text-sm text-slate-600">{message}</p> : null}
            <button disabled={saving} className="rounded-full bg-ink-800 px-5 py-3 text-sm font-medium text-white disabled:opacity-60">
              {saving ? "Saving..." : "Save preferences"}
            </button>
          </form>
        ) : null}
      </section>
    </main>
  );
}
