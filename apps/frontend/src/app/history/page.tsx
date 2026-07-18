"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { motion, AnimatePresence } from "framer-motion";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { LoadingState } from "@/components/ui/loading-state";
import { EmptyState } from "@/components/ui/empty-state";
import { useAppIntl } from "@/providers/intl-provider";
import { apiFetch } from "@/services/api";
import { fetchMe } from "@/services/auth";
import { cn } from "@/lib/cn";
import { formatDateKey } from "@/lib/date";
import { FadeIn, FadeInUp } from "@/lib/motion";

// ── Types ──

type Task = {
  id: string;
  title: string;
  description: string | null;
  deadline: string | null;
  start_time: string | null;
  task_type: string;
  priority: string | null;
  estimated_duration: number | null;
  status: string;
  tags: string[];
  completed_at: string | null;
};

type HistoryDay = {
  date: string;
  total: number;
  completed: number;
  pending: number;
  tasks: Task[];
};

type HistoryData = {
  days: HistoryDay[];
  from_date: string;
  to_date: string;
  total_tasks: number;
  total_completed: number;
  total_pending: number;
};

// ── Config ──

const statusBadge: Record<string, { variant: "coral" | "sky" | "mint" | "lavender" | "neutral" | "warning"; labelKey: string }> = {
  todo: { variant: "neutral", labelKey: "tasks.status.todo" },
  completed: { variant: "mint", labelKey: "tasks.status.completed" },
  skipped: { variant: "warning", labelKey: "tasks.status.skipped" },
  deferred: { variant: "lavender", labelKey: "tasks.status.deferred" },
  planned: { variant: "sky", labelKey: "tasks.status.planned" },
  draft: { variant: "neutral", labelKey: "tasks.status.draft" },
  generated: { variant: "coral", labelKey: "tasks.status.generated" },
};

type FilterMode = "all" | "completed" | "pending";

// ── Helpers ──

function getWeekStart(date: Date): Date {
  const d = new Date(date);
  const day = d.getDay();
  d.setDate(d.getDate() - day);
  d.setHours(0, 0, 0, 0);
  return d;
}

function getWeekEnd(date: Date): Date {
  const d = getWeekStart(date);
  d.setDate(d.getDate() + 6);
  return d;
}

function formatWeekLabel(date: Date, locale: string): string {
  const start = getWeekStart(date);
  const end = getWeekEnd(date);
  const fmt = new Intl.DateTimeFormat(locale === "vi" ? "vi-VN" : "en-US", { month: "short", day: "numeric" });
  return `${fmt.format(start)} — ${fmt.format(end)}`;
}

function isThisWeek(date: Date): boolean {
  const now = new Date();
  const ws = getWeekStart(now);
  const we = getWeekEnd(now);
  return date >= ws && date <= we;
}

function formatDateYMD(dateStr: string, locale: string): string {
  const d = new Date(dateStr + "T00:00:00");
  return new Intl.DateTimeFormat(locale === "vi" ? "vi-VN" : "en-US", {
    weekday: "short",
    month: "short",
    day: "numeric",
  }).format(d);
}

function getYesterdayStr(): string {
  const y = new Date();
  y.setDate(y.getDate() - 1);
  return formatDateKey(y);
}

// ── Page ──

export default function HistoryPage() {
  const router = useRouter();
  const tHistory = useTranslations("history");
  const tTasks = useTranslations("tasks");
  const { locale } = useAppIntl();

  const [history, setHistory] = useState<HistoryData | null>(null);
  const [loading, setLoading] = useState(true);
  const [weekOffset, setWeekOffset] = useState(0);
  const [filter, setFilter] = useState<FilterMode>("all");
  const [searchQuery, setSearchQuery] = useState("");

  // ── Determine the week range based on offset ──

  const weekStart = useMemo(() => {
    const base = new Date();
    base.setDate(base.getDate() + weekOffset * 7);
    return getWeekStart(base);
  }, [weekOffset]);

  const weekEnd = useMemo(() => getWeekEnd(weekStart), [weekStart]);

  // ── Clamp week navigation to the 30-day history range ──

  const { minWeekOffset, maxWeekOffset } = useMemo(() => {
    if (!history) return { minWeekOffset: -100, maxWeekOffset: 0 };
    const currentWeekStart = getWeekStart(new Date());

    const fromDate = new Date(history.from_date + "T00:00:00");
    const fromWeekStart = getWeekStart(fromDate);
    const minRaw = Math.round((fromWeekStart.getTime() - currentWeekStart.getTime()) / (7 * 24 * 60 * 60 * 1000));

    const toDate = new Date(history.to_date + "T00:00:00");
    const toWeekStart = getWeekStart(toDate);
    const maxRaw = Math.round((toWeekStart.getTime() - currentWeekStart.getTime()) / (7 * 24 * 60 * 60 * 1000));

    return { minWeekOffset: minRaw, maxWeekOffset: Math.max(maxRaw, -100) };
  }, [history]);

  // ── Fetch history (yesterday back 30 days) ──

  async function load() {
    try {
      await fetchMe();
      const yesterday = formatDateKey(new Date(Date.now() - 24 * 60 * 60 * 1000));
      const thirtyDaysAgo = formatDateKey(new Date(Date.now() - 31 * 24 * 60 * 60 * 1000));
      const data = await apiFetch<HistoryData>(`/tasks/history?from_date=${thirtyDaysAgo}&to_date=${yesterday}`);
      setHistory(data);
    } catch {
      router.push("/login");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  // Clamp offset whenever bounds change
  useEffect(() => {
    setWeekOffset((prev) => Math.max(minWeekOffset, Math.min(prev, maxWeekOffset)));
  }, [minWeekOffset, maxWeekOffset]);

  // ── Filter & group tasks for the current week ──

  function matchesSearch(task: Task): boolean {
    if (!searchQuery.trim()) return true;
    const q = searchQuery.toLowerCase();
    return (
      task.title.toLowerCase().includes(q) ||
      (task.description ?? "").toLowerCase().includes(q) ||
      task.tags.some((tag) => tag.toLowerCase().includes(q))
    );
  }

  const weekTasks = useMemo(() => {
    if (!history) return [];

    const ws = formatDateKey(weekStart);
    const we = formatDateKey(weekEnd);

    return history.days
      .filter((day) => day.date >= ws && day.date <= we)
      .map((day) => {
        let filtered = day.tasks;
        if (filter === "completed") filtered = filtered.filter((t) => t.status === "completed");
        else if (filter === "pending") filtered = filtered.filter((t) => t.status !== "completed");
        if (searchQuery.trim()) filtered = filtered.filter(matchesSearch);
        return { ...day, tasks: filtered };
      })
      .filter((day) => day.tasks.length > 0);
  }, [history, weekStart, weekEnd, filter, searchQuery]);

  const weekCompleted = useMemo(
    () => weekTasks.reduce((sum, d) => sum + d.tasks.filter((t) => t.status === "completed").length, 0),
    [weekTasks]
  );
  const weekTotal = useMemo(() => weekTasks.reduce((sum, d) => sum + d.tasks.length, 0), [weekTasks]);

  // ── Yesterday's overdue tasks (only when viewing this week) ──

  const yesterdayStr = useMemo(() => getYesterdayStr(), []);
  const yesterdayOverdueTasks = useMemo(() => {
    if (!history || weekOffset !== maxWeekOffset) return [];
    const yesterdayDay = history.days.find((d) => d.date === yesterdayStr);
    if (!yesterdayDay) return [];
    let tasks = yesterdayDay.tasks.filter((t) => t.status !== "completed");
    if (searchQuery.trim()) tasks = tasks.filter(matchesSearch);
    return tasks;
  }, [history, weekOffset, maxWeekOffset, yesterdayStr, searchQuery]);

  const canGoPrev = weekOffset > minWeekOffset;
  const canGoNext = weekOffset < maxWeekOffset;

  // ── Loading state ──

  if (loading) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <FadeIn className="space-y-6">
          <LoadingState lines={1} variant="card" />
          <LoadingState lines={4} variant="card" />
        </FadeIn>
      </main>
    );
  }

  // ── No history ──

  if (!history || history.days.length === 0) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <motion.div className="space-y-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
          <FadeInUp>
            <p className="section-label text-coral-500">{tHistory("eyebrow")}</p>
            <h1 className="page-title mt-1">{tHistory("title")}</h1>
            <p className="mt-1 text-sm text-neutral-500">{tHistory("description")}</p>
          </FadeInUp>
          <EmptyState illustration="tasks" title={tHistory("empty.title")} description={tHistory("empty.description")} />
        </motion.div>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
      <motion.div className="space-y-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>

        {/* ===== HEADER ===== */}
        <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
          <FadeInUp>
            <p className="section-label text-coral-500">{tHistory("eyebrow")}</p>
            <h1 className="page-title mt-1">{tHistory("title")}</h1>
            <p className="mt-1 text-sm text-neutral-500">
              {history.from_date} — {history.to_date} &middot; {tHistory("stats", { completed: history.total_completed.toString(), total: history.total_tasks.toString() })}
            </p>
          </FadeInUp>
        </div>

        {/* ===== WEEK NAVIGATION ===== */}
        <motion.div
          className="flex items-center justify-between rounded-[20px] border border-border-light bg-white/70 px-4 py-3 shadow-sm backdrop-blur-sm"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1, duration: 0.4 }}
        >
          <motion.button
            onClick={() => canGoPrev && setWeekOffset((p) => p - 1)}
            className={cn(
              "flex items-center gap-1 rounded-[12px] px-3 py-2 text-sm font-medium transition-colors",
              canGoPrev
                ? "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700"
                : "text-neutral-300 cursor-not-allowed"
            )}
            whileHover={canGoPrev ? { x: -2 } : {}}
            whileTap={canGoPrev ? { scale: 0.95 } : {}}
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
            <span className="hidden sm:inline">{tHistory("prevWeek")}</span>
          </motion.button>

          <div className="text-center">
            <p className={cn("font-display text-base font-semibold text-neutral-900")}>
              {tHistory("week", { date: formatWeekLabel(weekStart, locale) })}
            </p>
            <p className="mt-0.5 text-xs text-neutral-400">{formatWeekLabel(weekStart, locale)}</p>
          </div>

          <motion.button
            onClick={() => canGoNext && setWeekOffset((p) => p + 1)}
            className={cn(
              "flex items-center gap-1 rounded-[12px] px-3 py-2 text-sm font-medium transition-colors",
              canGoNext
                ? "text-neutral-500 hover:bg-neutral-100 hover:text-neutral-700"
                : "text-neutral-300 cursor-not-allowed"
            )}
            whileHover={canGoNext ? { x: 2 } : {}}
            whileTap={canGoNext ? { scale: 0.95 } : {}}
          >
            <span className="hidden sm:inline">{tHistory("nextWeek")}</span>
            <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
          </motion.button>
        </motion.div>

        {/* ===== WEEK STATS ===== */}
        <motion.div
          className="grid grid-cols-3 gap-2 sm:gap-3"
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.15, duration: 0.4 }}
        >
          <div className="rounded-[14px] sm:rounded-[16px] border border-border-light bg-white/60 p-3 sm:p-4 text-center shadow-sm">
            <p className="text-xl sm:text-2xl font-semibold text-neutral-900">{weekTotal}</p>
            <p className="mt-0.5 text-[10px] sm:text-xs text-neutral-400">{tHistory("stats", { completed: weekCompleted.toString(), total: weekTotal.toString() })}</p>
          </div>
          <div className="rounded-[14px] sm:rounded-[16px] border border-mint-100 bg-mint-50/40 p-3 sm:p-4 text-center shadow-sm">
            <p className="text-xl sm:text-2xl font-semibold text-mint-600">{weekCompleted}</p>
            <p className="mt-0.5 text-[10px] sm:text-xs text-mint-500">{tHistory("completed")}</p>
          </div>
          <div className="rounded-[14px] sm:rounded-[16px] border border-coral-100 bg-coral-50/40 p-3 sm:p-4 text-center shadow-sm">
            <p className="text-xl sm:text-2xl font-semibold text-coral-500">{weekTotal - weekCompleted}</p>
            <p className="mt-0.5 text-[10px] sm:text-xs text-coral-400">{tHistory("pending")}</p>
          </div>
        </motion.div>

        {/* ===== FILTER TABS + SEARCH ===== */}
        <motion.div
          className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.2 }}
        >
          <div className="flex gap-1 rounded-soft border border-border-light bg-white/60 p-1 w-fit">
            {(["all", "completed", "pending"] as const).map((mode) => (
              <motion.button
                key={mode}
                onClick={() => setFilter(mode)}
                className={cn(
                  "rounded-[10px] px-4 py-1.5 text-xs font-medium transition-all duration-200",
                  filter === mode ? "bg-white text-neutral-900 shadow-sm" : "text-neutral-500 hover:text-neutral-700"
                )}
                whileHover={{ y: -1 }}
                whileTap={{ scale: 0.97 }}
              >
                {mode === "all" ? "All" : mode === "completed" ? tHistory("completed") : tHistory("pending")}
              </motion.button>
            ))}
          </div>

          {/* Search */}
          <div className="relative w-full sm:w-64">
            <svg viewBox="0 0 24 24" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
            </svg>
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder={tTasks("search")}
              className="input-base pl-9 h-10 text-sm"
            />
            {searchQuery && (
              <button
                onClick={() => setSearchQuery("")}
                className="absolute right-2.5 top-1/2 -translate-y-1/2 rounded-full p-1 text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600"
              >
                <svg viewBox="0 0 12 12" className="h-3 w-3 fill-current">
                  <path d="M2.22 2.22a.75.75 0 011.06 0L6 4.94l2.72-2.72a.75.75 0 111.06 1.06L7.06 6l2.72 2.72a.75.75 0 11-1.06 1.06L6 7.06l-2.72 2.72a.75.75 0 01-1.06-1.06L4.94 6 2.22 3.28a.75.75 0 010-1.06z" />
                </svg>
              </button>
            )}
          </div>
        </motion.div>

        {/* ===== YESTERDAY'S OVERDUE (view-only, no edit) ===== */}
        <AnimatePresence>
          {yesterdayOverdueTasks.length > 0 && (
            <motion.div
              key="yesterday-overdue"
              initial={{ opacity: 0, y: -10, scale: 0.98 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: -10, scale: 0.98 }}
              transition={{ duration: 0.4 }}
            >
              <Card variant="ambient" className="overflow-hidden border-coral-100">
                <div className="absolute left-0 top-0 h-full w-1 bg-coral-400" />
                <div className="p-5 sm:p-6">
                  <div className="mb-3 flex items-center gap-2">
                    <div className="flex h-7 w-7 items-center justify-center rounded-full bg-coral-50 text-coral-500">
                      <svg viewBox="0 0 20 20" className="h-3.5 w-3.5 fill-current">
                        <path fillRule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clipRule="evenodd" />
                      </svg>
                    </div>
                    <h3 className="font-display text-sm font-semibold text-coral-600">{tHistory("yesterdayOverdue.title")}</h3>
                    <span className="rounded-full bg-coral-50 px-2 py-0.5 text-[11px] font-medium text-coral-500">{yesterdayOverdueTasks.length}</span>
                  </div>
                  <p className="mb-3 text-sm text-coral-500/70">{tHistory("yesterdayOverdue.notice")}</p>
                  <div className="grid gap-2">
                    {yesterdayOverdueTasks.map((task, i) => (
                      <motion.div
                        key={task.id}
                        className="flex items-center gap-3 rounded-[14px] border border-coral-100/60 bg-white/70 px-4 py-3 transition-all hover:border-coral-200"
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: i * 0.06, duration: 0.3 }}
                      >
                        <div className="h-2 w-2 shrink-0 rounded-full bg-coral-300" />
                        <span className="flex-1 truncate text-sm font-medium text-neutral-800">{task.title}</span>
                        {task.start_time && (
                          <span className="shrink-0 text-xs text-neutral-400">{task.start_time}</span>
                        )}
                        {task.priority === "urgent" && (
                          <Badge variant="coral" size="sm">{tTasks("priority.urgent")}</Badge>
                        )}
                      </motion.div>
                    ))}
                  </div>
                </div>
              </Card>
            </motion.div>
          )}
        </AnimatePresence>

        {/* ===== DAYS & TASKS (view-only, no edit) ===== */}
        {weekTasks.length > 0 ? (
          <div className="space-y-4">
            {weekTasks.map((day, dayIdx) => {
              const isYesterday = day.date === yesterdayStr;
              return (
                <motion.div
                  key={day.date}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: dayIdx * 0.05, duration: 0.4 }}
                >
                  <Card variant="glass" className={cn("overflow-hidden", isYesterday && "ring-1 ring-coral-100/40")}>
                    {/* Day header */}
                    <div className={cn(
                      "flex items-center justify-between border-b border-border-light px-5 py-3 sm:px-6",
                      isYesterday && "bg-coral-50/20"
                    )}>
                      <div className="flex items-center gap-3">
                        <div className={cn(
                          "flex h-8 w-8 items-center justify-center rounded-[10px] text-xs font-semibold",
                          day.tasks.every((t) => t.status === "completed")
                            ? "bg-mint-50 text-mint-600"
                            : day.tasks.some((t) => t.status !== "completed" && t.deadline && t.deadline < formatDateKey())
                              ? "bg-coral-50 text-coral-500"
                              : "bg-neutral-50 text-neutral-500"
                        )}>
                          {new Date(day.date + "T00:00:00").getDate()}
                        </div>
                        <div>
                          <p className="text-sm font-semibold text-neutral-900">
                            {formatDateYMD(day.date, locale)}
                          </p>
                          <p className="text-xs text-neutral-400">
                            {day.tasks.filter((t) => t.status === "completed").length}/{day.tasks.length} {tHistory("completed")}
                          </p>
                        </div>
                      </div>
                      <div className="flex items-center gap-2">
                        {isYesterday && (
                          <span className="rounded-full bg-coral-50 px-2.5 py-0.5 text-[11px] font-medium text-coral-500">
                            {tHistory("yesterdayOverdue.title")}
                          </span>
                        )}
                        {day.tasks.filter((t) => t.status === "completed").length === day.tasks.length && day.tasks.length > 0 && (
                          <Badge variant="mint" size="sm">{tHistory("completed")}</Badge>
                        )}
                      </div>
                    </div>

                    {/* Task list (no edit) */}
                    <div className="divide-y divide-border-light/50">
                      {day.tasks.map((task, i) => {
                        const isOverdueFromYesterday = isYesterday && task.status !== "completed";
                        return (
                          <motion.div
                            key={task.id}
                            className={cn(
                              "flex items-center gap-3 px-5 py-3 transition-colors sm:px-6 hover:bg-neutral-50/50",
                              task.status === "completed" && "opacity-60"
                            )}
                            initial={{ opacity: 0, x: -5 }}
                            animate={{ opacity: 1, x: 0 }}
                            transition={{ delay: i * 0.03, duration: 0.3 }}
                          >
                            {/* Status indicator */}
                            <div className={cn(
                              "h-2 w-2 shrink-0 rounded-full",
                              task.status === "completed" ? "bg-mint-400" :
                              task.status === "skipped" ? "bg-neutral-300" :
                              task.status === "deferred" ? "bg-lavender-400" :
                              isOverdueFromYesterday ? "bg-coral-400" :
                              "bg-sky-400"
                            )} />

                            {/* Task info */}
                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2">
                                <p className={cn(
                                  "truncate text-sm font-medium",
                                  task.status === "completed" ? "text-neutral-500 line-through" : "text-neutral-900"
                                )}>
                                  {task.title}
                                </p>
                                {task.status !== "completed" && isOverdueFromYesterday && (
                                  <span className="shrink-0 rounded-full bg-coral-50 px-2 py-0.5 text-[10px] font-medium text-coral-500">
                                    {tTasks("overdue.itemNote")}
                                  </span>
                                )}
                              </div>
                              <div className="mt-0.5 flex flex-wrap items-center gap-x-3 gap-y-0.5 text-xs text-neutral-400">
                                {task.start_time && (
                                  <span className="inline-flex items-center gap-1">
                                    <svg viewBox="0 0 24 24" className="h-3 w-3 fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></svg>
                                    {task.start_time}
                                  </span>
                                )}
                                {task.estimated_duration && (
                                  <span>{Math.floor(task.estimated_duration / 60)}h {task.estimated_duration % 60}m</span>
                                )}
                                {task.description && (
                                  <span className="truncate max-w-[200px] text-neutral-400">&middot; {task.description}</span>
                                )}
                              </div>
                            </div>

                            {/* Badges */}
                            <div className="flex shrink-0 items-center gap-2">
                              {task.task_type === "flexible" && (
                                <Badge variant="lavender" size="sm">{tTasks("taskType.flexible")}</Badge>
                              )}
                              {task.priority && task.priority !== "normal" && (
                                <Badge
                                  variant={task.priority === "urgent" ? "coral" : task.priority === "high" ? "warning" : "neutral"}
                                  size="sm"
                                >
                                  {tTasks(`priority.${task.priority}`)}
                                </Badge>
                              )}
                              {statusBadge[task.status] && (
                                <Badge variant={statusBadge[task.status].variant} size="sm" dot>
                                  {tTasks(`status.${task.status}`)}
                                </Badge>
                              )}
                            </div>
                          </motion.div>
                        );
                      })}
                    </div>
                  </Card>
                </motion.div>
              );
            })}
          </div>
        ) : (
          <FadeInUp>
            <Card variant="ambient" className="p-10 text-center">
              <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-2xl bg-neutral-50 text-neutral-400">
                <svg viewBox="0 0 24 24" className="h-6 w-6 fill-none stroke-current stroke-[1.8]">
                  <rect x="3" y="4" width="18" height="18" rx="2" />
                  <path d="M16 2v4M8 2v4M3 10h18" />
                </svg>
              </div>
              <p className="text-sm font-medium text-neutral-600">{tHistory("noTasks")}</p>
            </Card>
          </FadeInUp>
        )}

        {/* ===== BOTTOM PAGINATION ===== */}
        <motion.div
          className="flex items-center justify-center gap-2 sm:gap-4 pt-2 pb-4 sm:pb-8"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ delay: 0.3 }}
        >
          <motion.button
            onClick={() => canGoPrev && setWeekOffset((p) => p - 1)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-pill border bg-white text-sm font-medium shadow-sm transition-all",
              "px-3 sm:px-4 py-2.5 sm:py-2",
              canGoPrev
                ? "border-border-light text-neutral-600 hover:border-neutral-300"
                : "border-neutral-100 text-neutral-300 cursor-not-allowed"
            )}
            whileHover={canGoPrev ? { y: -1 } : {}}
            whileTap={canGoPrev ? { scale: 0.97 } : {}}
          >
            <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
            <span className="hidden sm:inline">{tHistory("prevWeek")}</span>
          </motion.button>
          <motion.button
            onClick={() => setWeekOffset(maxWeekOffset)}
            className={cn(
              "inline-flex items-center rounded-pill border text-sm font-medium shadow-sm transition-all",
              "px-3 sm:px-4 py-2.5 sm:py-2",
              weekOffset === maxWeekOffset
                ? "border-coral-200 bg-coral-50 text-coral-600"
                : "border-border-light bg-white text-neutral-600 hover:border-neutral-300"
            )}
            whileHover={{ y: -1 }}
            whileTap={{ scale: 0.97 }}
          >
            {tHistory("thisWeek")}
          </motion.button>
          <motion.button
            onClick={() => canGoNext && setWeekOffset((p) => p + 1)}
            className={cn(
              "inline-flex items-center gap-1.5 rounded-pill border bg-white text-sm font-medium shadow-sm transition-all",
              "px-3 sm:px-4 py-2.5 sm:py-2",
              canGoNext
                ? "border-border-light text-neutral-600 hover:border-neutral-300"
                : "border-neutral-100 text-neutral-300 cursor-not-allowed"
            )}
            whileHover={canGoNext ? { y: -1 } : {}}
            whileTap={canGoNext ? { scale: 0.97 } : {}}
          >
            <span className="hidden sm:inline">{tHistory("nextWeek")}</span>
            <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><path d="M5 12h14M12 5l7 7-7 7" /></svg>
          </motion.button>
        </motion.div>

        {/* ===== OVERALL STATS (footer) ===== */}
        {history && (
          <motion.div
            className="rounded-[20px] border border-border-light bg-white/50 px-6 py-4 text-center text-xs text-neutral-400 backdrop-blur-sm"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.35 }}
          >
            {tHistory("stats", { completed: history.total_completed.toString(), total: history.total_tasks.toString() })} &middot;{" "}
            {history.days.length} {history.days.length === 1 ? "day" : "days"} with tasks
          </motion.div>
        )}
      </motion.div>
    </main>
  );
}
