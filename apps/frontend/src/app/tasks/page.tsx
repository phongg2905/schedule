"use client";

import { Suspense, useEffect, useState } from "react";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useTranslations } from "next-intl";
import { motion, AnimatePresence } from "@/lib/motion";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { EmptyState } from "@/components/ui/empty-state";
import { LoadingState } from "@/components/ui/loading-state";
import dynamic from "next/dynamic";

// Lazy load Modal — only needed when user opens draft plan preview
const Modal = dynamic(() => import("@/components/ui/modal").then((mod) => mod.Modal), {
  ssr: false,
  loading: () => null,
});
import { getErrorMessage } from "@/lib/api-error";
import { useAppIntl } from "@/providers/intl-provider";
import { apiFetch } from "@/services/api";
import { fetchMe } from "@/services/auth";
import { cn } from "@/lib/cn";
import { formatDateKey } from "@/lib/date";
import { sortByTime } from "@/lib/sort";
import { SwipeableCard, swipeActions } from "@/components/ui/swipeable-card";
import { PullToRefresh } from "@/components/ui/pull-to-refresh";
import { FadeIn, FadeInDown } from "@/lib/motion";

export default function TasksPage() {
  return (
    <Suspense fallback={
      <main className="mx-auto w-full max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
        <div className="space-y-5 sm:space-y-6">
          <LoadingState lines={1} variant="card" />
          <LoadingState lines={4} variant="card" />
        </div>
      </main>
    }>
      <TasksPageContent />
    </Suspense>
  );
}

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

type DraftPlan = {
  id: string;
  plan_date: string;
  status: string;
  source: string;
  explanation: string | null;
  items: Array<{
    id: string;
    label: string;
    start_time: string;
    end_time: string;
    status: string;
    task_id: string | null;
  }>;
};

type Tab = "today" | "week" | "month";

const priorityBadge: Record<string, { variant: "coral" | "sky" | "mint" | "lavender" | "neutral" | "warning"; labelKey: string }> = {
  urgent: { variant: "coral", labelKey: "tasks.priority.urgent" },
  high: { variant: "warning", labelKey: "tasks.priority.high" },
  normal: { variant: "sky", labelKey: "tasks.priority.normal" },
  low: { variant: "neutral", labelKey: "tasks.priority.low" },
};

const statusBadge: Record<string, { variant: "coral" | "sky" | "mint" | "lavender" | "neutral" | "warning"; labelKey: string }> = {
  todo: { variant: "neutral", labelKey: "tasks.status.todo" },
  completed: { variant: "mint", labelKey: "tasks.status.completed" },
  skipped: { variant: "warning", labelKey: "tasks.status.skipped" },
  deferred: { variant: "lavender", labelKey: "tasks.status.deferred" },
  planned: { variant: "sky", labelKey: "tasks.status.planned" },
  draft: { variant: "neutral", labelKey: "tasks.status.draft" },
  generated: { variant: "coral", labelKey: "tasks.status.generated" },
};

const easeOut = [0.25, 0.1, 0.25, 1] as const;

function TasksPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const tTasks = useTranslations("tasks");
  const tErrors = useTranslations("errors");
  const { formatDate } = useAppIntl();

  const [tasks, setTasks] = useState<Task[]>([]);
  const [loading, setLoading] = useState(true);
  const [activeTab, setActiveTab] = useState<Tab>("today");
  const [searchQuery, setSearchQuery] = useState("");
  const [showMobileSearch, setShowMobileSearch] = useState(false);
  const [draftPlan, setDraftPlan] = useState<DraftPlan | null>(null);
  const [draftOpen, setDraftOpen] = useState(false);
  const [draftLoading, setDraftLoading] = useState(false);
  const [draftActionLoading, setDraftActionLoading] = useState<string | null>(null);
  const [draftError, setDraftError] = useState<string | null>(null);

  const weekDays = ["sun", "mon", "tue", "wed", "thu", "fri", "sat"] as const;

  function getWeekDates(): Date[] {
    const today = new Date();
    const dayOfWeek = today.getDay();
    const startOfWeek = new Date(today);
    startOfWeek.setDate(today.getDate() - dayOfWeek);
    return Array.from({ length: 7 }, (_, i) => {
      const d = new Date(startOfWeek);
      d.setDate(startOfWeek.getDate() + i);
      return d;
    });
  }

  function isToday(dateStr: string): boolean {
    return dateStr === formatDateKey();
  }

  function formatDraftTime(isoValue: string): string {
    return isoValue.slice(11, 16);
  }

  async function load() {
    try {
      await fetchMe();
      const [data, currentPlan] = await Promise.all([
        apiFetch<Task[]>("/tasks"),
        apiFetch<DraftPlan | null>("/daily-plans/today"),
      ]);
      setTasks(data);
      const isDraftPlan = Boolean(currentPlan && currentPlan.status === "draft");
      setDraftPlan(isDraftPlan ? currentPlan : null);
      setDraftOpen(isDraftPlan && searchParams.get("autoplan") === "1");
    } catch { router.push("/login"); }
    finally { setLoading(false); }
  }

  async function refreshPage() {
    try {
      const data = await apiFetch<Task[]>("/tasks");
      setTasks(data);
    } catch { /* silently fail */ }
  }

  useEffect(() => { void load(); }, []);

  useEffect(() => {
    if (loading) return;
    if (searchParams.get("autoplan") !== "1") return;
    if (draftPlan || draftLoading || draftActionLoading) return;
    router.replace("/tasks");
    void generateDraftPlan();
  }, [loading, searchParams, draftPlan, draftLoading, draftActionLoading, router]);

  async function generateDraftPlan() {
    setDraftLoading(true);
    setDraftActionLoading("generate");
    setDraftError(null);
    try {
      const plan = await apiFetch<DraftPlan>("/daily-plans/draft", {
        method: "POST",
        body: JSON.stringify({
          plan_date: formatDateKey(),
          context_window_type: "task_plan_draft",
          trigger_source: "manual",
        }),
      });
      setDraftPlan(plan);
      setDraftOpen(true);
    } catch (error) {
      setDraftError(getErrorMessage(error, tErrors));
    } finally {
      setDraftLoading(false);
      setDraftActionLoading(null);
    }
  }

  async function confirmDraftPlan() {
    if (!draftPlan) return;
    setDraftActionLoading("confirm");
    setDraftError(null);
    try {
      await apiFetch(`/daily-plans/${draftPlan.id}/confirm`, { method: "POST" });
      await load();
      setDraftOpen(false);
      setDraftPlan(null);
    } catch (error) {
      setDraftError(getErrorMessage(error, tErrors));
    } finally {
      setDraftActionLoading(null);
    }
  }

  async function discardDraftPlan() {
    if (!draftPlan) return;
    setDraftActionLoading("discard");
    setDraftError(null);
    try {
      await apiFetch(`/daily-plans/${draftPlan.id}`, { method: "DELETE" });
      setDraftOpen(false);
      setDraftPlan(null);
    } catch (error) {
      setDraftError(getErrorMessage(error, tErrors));
    } finally {
      setDraftActionLoading(null);
    }
  }

  async function regenerateDraftPlan() {
    setDraftLoading(true);
    setDraftActionLoading("regenerate");
    setDraftError(null);
    try {
      const plan = await apiFetch<DraftPlan>("/daily-plans/draft", {
        method: "POST",
        body: JSON.stringify({
          plan_date: formatDateKey(),
          context_window_type: "task_plan_draft",
          trigger_source: "manual",
        }),
      });
      setDraftPlan(plan);
      setDraftOpen(true);
    } catch (error) {
      setDraftError(getErrorMessage(error, tErrors));
    } finally {
      setDraftLoading(false);
      setDraftActionLoading(null);
    }
  }

  const filteredTasks = tasks.filter((t) =>
    searchQuery
      ? t.title.toLowerCase().includes(searchQuery.toLowerCase()) || t.tags?.some((tag) => tag.toLowerCase().includes(searchQuery.toLowerCase()))
      : true
  );

  function getRelativeDateStr(daysOffset: number): string {
    const date = new Date();
    date.setDate(date.getDate() + daysOffset);
    return formatDateKey(date);
  }

  const todayStr = formatDateKey();
  const yesterdayStr = getRelativeDateStr(-1);
  const tomorrowStr = getRelativeDateStr(1);

  const todayTasks = sortByTime(filteredTasks.filter((t) => t.deadline === todayStr && t.status !== "completed"));
  const completedTasks = filteredTasks
    .filter((t) => t.status === "completed" && t.completed_at && formatDateKey(new Date(t.completed_at)) === todayStr)
    .sort((a, b) => (b.completed_at ?? "").localeCompare(a.completed_at ?? ""));
  const upcomingTasks = sortByTime(filteredTasks.filter((t) => t.deadline === tomorrowStr && t.status !== "completed"));
  const overdueTasks = sortByTime(filteredTasks.filter((t) => t.deadline === yesterdayStr && t.status !== "completed"));

  const weekDates = getWeekDates();

  if (loading) {
    return (
      <main className="mx-auto w-full max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
        <FadeIn className="space-y-5 sm:space-y-6">
          <LoadingState lines={1} variant="card" />
          <LoadingState lines={4} variant="card" />
        </FadeIn>
      </main>
    );
  }

  return (
    <main className="mx-auto w-full max-w-7xl px-4 py-5 sm:px-6 lg:px-8">
      <PullToRefresh onRefresh={refreshPage}>
      <motion.div className="space-y-5 sm:space-y-6 lg:space-y-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
        {/* Header */}
        <div className="flex flex-col gap-3 sm:gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <FadeInDown>
              <p className="section-label text-coral-500">{tTasks("page.eyebrow")}</p>
            </FadeInDown>
            <motion.h1 className="page-title" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
              {tTasks("page.title")}
            </motion.h1>
            <motion.p className="mt-0.5 sm:mt-1 text-xs sm:text-sm text-neutral-500" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}>
              {tTasks("page.count", { count: tasks.length })}
            </motion.p>
          </div>
          <motion.div initial={{ opacity: 0, scale: 0.95 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.2 }} className="shrink-0">
            <div className="flex flex-wrap gap-2">
              <motion.div whileHover={{ y: -1 }} whileTap={{ scale: 0.98 }}>
                <Button
                  variant="soft"
                  size="md"
                  onClick={() => {
                    if (draftPlan) {
                      setDraftOpen(true);
                      return;
                    }
                    void generateDraftPlan();
                  }}
                  disabled={draftLoading || draftActionLoading !== null}
                  className="w-full sm:w-auto"
                >
                  <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]">
                    <path d="M12 3v18M3 12h18" />
                    <path d="M7 7l10 10" />
                  </svg>
                  <span className="hidden xs:inline">{draftPlan ? "Review draft" : "Auto plan"}</span>
                  <span className="xs:hidden">{draftPlan ? "Draft" : "Plan"}</span>
                </Button>
              </motion.div>
              <Link href="/tasks/new">
                <motion.div whileHover={{ y: -1 }} whileTap={{ scale: 0.98 }}>
                  <Button variant="primary" size="md" className="w-full sm:w-auto">
                    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><path d="M12 5v14M5 12h14" /></svg>
                    {tTasks("create.title")}
                  </Button>
                </motion.div>
              </Link>
            </div>
          </motion.div>
        </div>

        {/* Tabs & Search */}
        <motion.div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
          <div className="flex items-center gap-2 w-full sm:w-auto">
            <div className="flex gap-1 rounded-soft border border-border-light bg-white/60 p-1 overflow-x-auto flex-1 sm:flex-none">
              {(["today", "week", "month"] as const).map((tab) => (
                <motion.button
                  key={tab}
                  onClick={() => setActiveTab(tab)}
                  className={cn(
                    "rounded-[10px] px-2.5 sm:px-4 py-2 text-xs sm:text-sm font-medium transition-all duration-200 whitespace-nowrap",
                    activeTab === tab ? "bg-white text-neutral-900 shadow-sm" : "text-neutral-500 hover:text-neutral-700"
                  )}
                  whileHover={{ y: -1 }}
                  whileTap={{ scale: 0.97 }}
                >
                  {tTasks(`tabs.${tab}`)}
                </motion.button>
              ))}
            </div>
            {/* Mobile search toggle */}
            <button
              onClick={() => setShowMobileSearch(!showMobileSearch)}
              className="sm:hidden flex h-9 w-9 shrink-0 items-center justify-center rounded-[10px] text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600"
              aria-label={tTasks("search")}
            >
              <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]">
                <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
              </svg>
            </button>
          </div>
          <div className={cn("relative w-full sm:max-w-xs", showMobileSearch ? "block" : "hidden sm:block")}>
            <svg viewBox="0 0 24 24" className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-neutral-400" fill="none" stroke="currentColor" strokeWidth="2">
              <circle cx="11" cy="11" r="8" /><path d="M21 21l-4.35-4.35" />
            </svg>
            <Input placeholder={tTasks("search")} value={searchQuery} onChange={(e) => setSearchQuery(e.target.value)} className="pl-9 h-10 sm:h-auto" />
          </div>
        </motion.div>

        {/* ── TODAY VIEW ── */}
        {activeTab === "today" && (
          <AnimatePresence mode="wait">
            <motion.div key="today-view" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} className="space-y-6">
              {overdueTasks.length > 0 && (
                <section>
                  <div className="mb-3 flex items-center gap-2">
                    <h2 className="font-display text-lg font-semibold text-coral-600">{tTasks("filter.urgent")}</h2>
                    <span className="rounded-full bg-coral-50 px-2.5 py-0.5 text-xs font-medium text-coral-500">{overdueTasks.length}</span>
                  </div>
                  <div className="mb-3 rounded-[18px] border border-coral-100 bg-coral-50/60 px-4 py-3 text-sm text-coral-700">
                    {tTasks("overdue.notice")}
                  </div>
                  <div className="grid gap-2">
                    {overdueTasks.map((task, i) => (
                      <TaskCard key={task.id} task={task} formatDate={formatDate} delay={i * 0.05} overdue compact />
                    ))}
                  </div>
                </section>
              )}

              <section>
                <div className="mb-3 flex items-center gap-2">
                  <h2 className="font-display text-lg font-semibold text-neutral-800">{tTasks("tabs.today")}</h2>
                  <span className="rounded-full bg-coral-50 px-2.5 py-0.5 text-xs font-medium text-coral-500">{todayTasks.length}</span>
                </div>
                {todayTasks.length > 0 ? (
                  <div className="grid gap-2">
                    {todayTasks.map((task, i) => (
                      <Link key={task.id} href={`/tasks/${task.id}`}>
                        <TaskCard task={task} formatDate={formatDate} delay={i * 0.05} />
                      </Link>
                    ))}
                  </div>
                ) : (
                  <Card variant="ambient" className="p-8 text-center">
                    <p className="text-sm text-neutral-500">{tTasks("empty.title")}</p>
                  </Card>
                )}
              </section>

              {upcomingTasks.length > 0 && (
                <section>
                  <div className="mb-3 flex items-center gap-2">
                    <h2 className="font-display text-lg font-semibold text-neutral-800">{tTasks("filter.tomorrow")}</h2>
                    <span className="rounded-full bg-sky-50 px-2.5 py-0.5 text-xs font-medium text-sky-500">{upcomingTasks.length}</span>
                  </div>
                  <div className="grid gap-2">
                    {upcomingTasks.map((task, i) => (
                      <Link key={task.id} href={`/tasks/${task.id}`}>
                        <TaskCard task={task} formatDate={formatDate} delay={i * 0.05} />
                      </Link>
                    ))}
                  </div>
                </section>
              )}

              {completedTasks.length > 0 && (
                <section>
                  <div className="mb-3 flex items-center gap-2">
                    <h2 className="font-display text-lg font-semibold text-neutral-500">{tTasks("filter.completed")}</h2>
                    <span className="rounded-full bg-mint-50 px-2.5 py-0.5 text-xs font-medium text-mint-500">{completedTasks.length}</span>
                  </div>
                  <div className="grid gap-2">
                    {completedTasks.slice(0, 5).map((task, i) => (
                      <Link key={task.id} href={`/tasks/${task.id}`}>
                        <TaskCard task={task} formatDate={formatDate} delay={i * 0.03} completed />
                      </Link>
                    ))}
                  </div>
                </section>
              )}

              {todayTasks.length === 0 && upcomingTasks.length === 0 && completedTasks.length === 0 && (
                <EmptyState illustration="tasks" title={tTasks("empty.title")} description={tTasks("empty.description")} actionHref="/tasks/new" actionLabel={tTasks("empty.action")} />
              )}
            </motion.div>
          </AnimatePresence>
        )}

        {/* ── WEEK VIEW ── */}
        {activeTab === "week" && (
          <AnimatePresence mode="wait">
            <motion.div key="week-view" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <Card variant="glass" className="overflow-hidden">
                <div className="overflow-x-auto pb-2 md:pb-0 -mx-1 sm:mx-0 scrollbar-thin">
                <div className="grid min-h-[300px] sm:min-h-[350px] min-w-[500px] sm:min-w-[600px] grid-cols-7 divide-x divide-border-light md:min-w-0">
                  {weekDates.map((date, idx) => {
                    const dateStr = formatDateKey(date);
                    const dayTasks = sortByTime(filteredTasks.filter((t) => t.deadline === dateStr));
                    const dayName = weekDays[date.getDay()];
                    const isTodayDate = isToday(dateStr);
                    return (
                      <motion.div
                        key={dateStr}
                        className={cn("flex flex-col p-3 transition-colors", isTodayDate ? "bg-coral-50/30" : "bg-white/30 hover:bg-neutral-50/50")}
                        initial={{ opacity: 0, y: 10 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ delay: idx * 0.05 }}
                      >
                        <div className={cn("mb-2 text-center", isTodayDate && "font-semibold")}>
                          <p className="text-[10px] sm:text-[11px] font-semibold uppercase tracking-wider text-neutral-400">{tTasks(`week.${dayName}`).substring(0,3)}</p>
                          <p className={cn("mt-0.5 text-base sm:text-lg font-semibold", isTodayDate ? "text-coral-500" : "text-neutral-700")}>{date.getDate()}</p>
                        </div>
                        <div className="flex-1 space-y-1">
                          {dayTasks.slice(0, 4).map((task) => (
                            <Link key={task.id} href={`/tasks/${task.id}`}>
                              <div className={cn(
                                "rounded-lg px-2 py-1.5 text-xs transition-all hover:shadow-sm",
                                task.status === "completed" ? "bg-mint-50 text-mint-600 line-through" : "bg-coral-50 text-coral-700"
                              )}>
                                <p className="truncate font-medium">{task.title}</p>
                              </div>
                            </Link>
                          ))}
                          {dayTasks.length > 4 ? (
                            <p className="text-[11px] font-medium text-neutral-400 text-center pt-1">+{dayTasks.length - 4} more</p>
                          ) : dayTasks.length === 0 ? (
                            <p className="text-[11px] text-neutral-300 text-center pt-2">{tTasks("week.noTasks")}</p>
                          ) : null}
                        </div>
                      </motion.div>
                    );
                  })}
                  </div>
              </div>
              </Card>
            </motion.div>
          </AnimatePresence>
        )}

        {/* ── MONTH VIEW (Placeholder) ── */}
        {activeTab === "month" && (
          <AnimatePresence mode="wait">
            <motion.div key="month-view" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <Card variant="glass" className="p-8 sm:p-12">
                <div className="mx-auto max-w-md text-center">
                  <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-2xl bg-gradient-to-br from-lavender-50 to-lavender-100 text-lavender-400">
                    <svg viewBox="0 0 24 24" className="h-8 w-8 fill-none stroke-current stroke-[1.8]">
                      <rect x="3" y="4" width="18" height="18" rx="2" />
                      <path d="M16 2v4M8 2v4M3 10h18" />
                      <path d="M8 14h.01M12 14h.01M16 14h.01M8 18h.01M12 18h.01M16 18h.01" />
                    </svg>
                  </div>
                  <h2 className="font-display text-2xl font-semibold text-neutral-900">{tTasks("month.title")}</h2>
                  <p className="mt-2 text-sm text-neutral-500">{tTasks("month.comingSoon")}</p>
                  <p className="mt-1 text-xs text-neutral-400">{tTasks("month.comingSoonDesc")}</p>
                  <div className="mt-8 space-y-4 text-left">
                    <div className="rounded-soft border border-border-light bg-white/50 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-neutral-400 mb-2">{tTasks("month.goals")}</p>
                      <p className="text-sm italic text-neutral-400">{tTasks("month.goalPlaceholder")}</p>
                    </div>
                    <div className="rounded-soft border border-dashed border-lavender-200 bg-lavender-50/30 p-4">
                      <p className="text-xs font-semibold uppercase tracking-wider text-lavender-400 mb-2">{tTasks("month.roadmap")}</p>
                      <p className="text-sm italic text-neutral-400">{tTasks("month.roadmapPlaceholder")}</p>
                    </div>
                  </div>
                </div>
              </Card>
            </motion.div>
          </AnimatePresence>
        )}
      </motion.div>
      </PullToRefresh>

      <Modal
        open={draftOpen}
        onClose={() => setDraftOpen(false)}
        title="Draft plan preview"
        description={draftPlan ? `${draftPlan.plan_date} · ${draftPlan.items.length} item(s)` : "Generate a draft to review before saving to tasks."}
        className="max-w-3xl"
      >
        <div className="space-y-5">
          {draftError ? (
            <div className="rounded-2xl border border-coral-100 bg-coral-50 px-4 py-3 text-sm text-coral-700">
              {draftError}
            </div>
          ) : null}

          {draftPlan ? (
            <>
              <div className="rounded-2xl border border-border-light bg-neutral-50/70 px-4 py-3">
                <p className="text-xs font-semibold uppercase tracking-wider text-neutral-400">Plan status</p>
                <div className="mt-2 flex flex-wrap items-center gap-2">
                  <Badge variant="sky" size="sm">{draftPlan.status}</Badge>
                  <Badge variant="neutral" size="sm">{draftPlan.source}</Badge>
                </div>
                {draftPlan.explanation ? <p className="mt-3 text-sm leading-6 text-neutral-600">{draftPlan.explanation}</p> : null}
              </div>

              <div className="max-h-[48vh] space-y-2 overflow-y-auto pr-1">
                {draftPlan.items.length > 0 ? draftPlan.items.map((item, index) => (
                  <Card key={item.id} variant="ambient" className="border border-border-light p-4">
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0">
                        <div className="flex items-center gap-2">
                          <p className="font-medium text-neutral-900">{index + 1}. {item.label}</p>
                          <Badge variant="lavender" size="sm">{item.status}</Badge>
                        </div>
                        <p className="mt-1 text-sm text-neutral-500">
                          {formatDraftTime(item.start_time)} - {formatDraftTime(item.end_time)}
                        </p>
                      </div>
                      {item.task_id ? <Badge variant="neutral" size="sm">task linked</Badge> : null}
                    </div>
                  </Card>
                )) : (
                  <Card variant="ambient" className="border border-dashed border-border-light p-6 text-center">
                    <p className="text-sm text-neutral-500">No items were generated for this date.</p>
                  </Card>
                )}
              </div>

              <div className="flex flex-wrap justify-end gap-2 border-t border-border-light pt-4">
                <Button
                  variant="ghost"
                  onClick={() => void discardDraftPlan()}
                  disabled={draftActionLoading !== null}
                >
                  {draftActionLoading === "discard" ? "Discarding..." : "Discard"}
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => void regenerateDraftPlan()}
                  disabled={draftLoading || draftActionLoading !== null}
                >
                  {draftLoading || draftActionLoading === "regenerate" ? "Regenerating..." : "Regenerate"}
                </Button>
                <Button
                  variant="primary"
                  onClick={() => void confirmDraftPlan()}
                  disabled={draftActionLoading !== null}
                >
                  {draftActionLoading === "confirm" ? "Confirming..." : "Confirm"}
                </Button>
              </div>
            </>
          ) : (
            <div className="rounded-2xl border border-border-light bg-neutral-50/70 px-4 py-6 text-sm text-neutral-500">
              No draft is currently loaded.
            </div>
          )}
        </div>
      </Modal>
    </main>
  );
}

// ── Task Card Sub-component ──

type TaskCardProps = {
  task: Task;
  formatDate: (d: string | Date) => string;
  delay?: number;
  overdue?: boolean;
  completed?: boolean;
  compact?: boolean;
};

function TaskCard({ task, formatDate, delay = 0, overdue = false, completed = false, compact = false }: Readonly<TaskCardProps>) {
  const tTasks = useTranslations("tasks");
  const priorityInfo = task.priority ? priorityBadge[task.priority] : null;
  const statusInfo = statusBadge[task.status];

  return (
    <motion.div
      initial={{ opacity: 0, y: 10, scale: 0.98 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      transition={{ delay, duration: 0.3, ease: easeOut }}
      className={cn(
        "group relative overflow-hidden rounded-[16px] border border-border-light bg-white p-4 shadow-sm transition-all duration-200 hover:shadow-card-hover",
        compact && "p-3 sm:p-4",
        overdue && "border-coral-100 bg-coral-50/20",
        completed && "opacity-60"
      )}
    >
      {overdue && <div className="absolute left-0 top-0 h-full w-1 rounded-l-[16px] bg-coral-400" />}
      {task.priority === "urgent" && !overdue && <div className="absolute left-0 top-0 h-full w-1 rounded-l-[16px] bg-coral-400" />}
      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2">
            <h3 className={cn("font-display text-base font-semibold text-neutral-900 truncate", compact && "text-[15px]", completed && "line-through")}>{task.title}</h3>
          </div>
          {!compact && task.description && <p className="mt-1 text-sm text-neutral-500 line-clamp-1">{task.description}</p>}
          {!compact && (
            <div className="mt-2 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-neutral-400">
              {task.start_time && <span className="inline-flex items-center gap-1"><svg viewBox="0 0 24 24" className="h-3 w-3 fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></svg>{task.start_time}</span>}
              {task.deadline && <span className="inline-flex items-center gap-1"><svg viewBox="0 0 24 24" className="h-3 w-3 fill-none stroke-current stroke-[1.8]"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></svg>{formatDate(task.deadline)}</span>}
              {task.estimated_duration && <span className="inline-flex items-center gap-1"><svg viewBox="0 0 24 24" className="h-3 w-3 fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></svg>{Math.floor(task.estimated_duration / 60)}h {task.estimated_duration % 60}m</span>}
            </div>
          )}
        </div>
        {!compact ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2">
            {task.task_type === "flexible" && <Badge variant="lavender" size="sm">{tTasks("taskType.flexible")}</Badge>}
            {priorityInfo && !completed && <Badge variant={priorityInfo.variant} size="sm">{tTasks(`priority.${task.priority}`)}</Badge>}
            {statusInfo && <Badge variant={statusInfo.variant} size="sm" dot>{tTasks(`status.${task.status}`)}</Badge>}
          </div>
        ) : null}
      </div>
    </motion.div>
  );
}
