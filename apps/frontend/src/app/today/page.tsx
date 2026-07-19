"use client";

import { useEffect, useMemo, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { motion, AnimatePresence } from "framer-motion";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ProgressRing } from "@/components/ui/progress-ring";
import { StatCard } from "@/components/ui/stat-card";
import { LoadingState } from "@/components/ui/loading-state";
import { EmptyState } from "@/components/ui/empty-state";
import { SectionHeader } from "@/components/ui/section-header";
import { getErrorMessage } from "@/lib/api-error";
import { cn } from "@/lib/cn";
import { useAppIntl } from "@/providers/intl-provider";
import { formatDateKey } from "@/lib/date";
import { sortByTime } from "@/lib/sort";
import { apiFetch } from "@/services/api";
import { fetchMe } from "@/services/auth";
import {
  FadeIn,
  FadeInUp,
  FadeInDown,
  StaggerContainer,
  StaggerItem,
  scaleIn,
} from "@/lib/motion";

// ── Types ──

type DailyPlan = {
  id: string;
  plan_date: string;
  status: string;
  source: string;
  explanation?: string | null;
  items: Array<{
    id: string;
    label: string;
    start_time: string;
    end_time: string;
    status: string;
    task_id: string | null;
  }>;
};

type Task = {
  id: string;
  title: string;
  description: string | null;
  deadline: string | null;
  start_time: string | null;
  priority: string | null;
  estimated_duration: number | null;
  status: string;
  tags: string[];
  completed_at: string | null;
};

type Insight = {
  summary_date: string;
  total_tasks: number;
  completed_tasks: number;
  skipped_tasks: number;
  deferred_tasks: number;
  pending_tasks: number;
  top_focus: string;
  highlights: string[];
};

function formatTime(isoString: string, locale: string): string {
  const date = new Date(isoString);
  return date.toLocaleTimeString(locale === "vi" ? "vi-VN" : "en-US", { hour: "2-digit", minute: "2-digit" });
}

function addMinutesToTime(dateKey: string, timeValue: string, minutesToAdd: number): string {
  const [hours, minutes] = timeValue.split(":").map((part) => Number(part));
  const totalMinutes = hours * 60 + minutes + minutesToAdd;
  const normalizedMinutes = ((totalMinutes % (24 * 60)) + 24 * 60) % (24 * 60);
  const nextHours = Math.floor(normalizedMinutes / 60);
  const nextMinutes = normalizedMinutes % 60;
  return `${dateKey}T${String(nextHours).padStart(2, "0")}:${String(nextMinutes).padStart(2, "0")}:00`;
}

function getGreetingKey(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "morning";
  if (hour < 17) return "afternoon";
  return "evening";
}

function getMotivationKey(): string {
  return `${new Date().getDate() % 6}`;
}

const easeTimeline = [0.25, 0.1, 0.25, 1] as const;

export default function TodayPage() {
  const router = useRouter();
  const tToday = useTranslations("today");
  const tErrors = useTranslations("errors");
  const { locale } = useAppIntl();

  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [insight, setInsight] = useState<Insight | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [aiExplaining, setAiExplaining] = useState(false);
  const [aiAdjusting, setAiAdjusting] = useState(false);
  const [busyAction, setBusyAction] = useState<string | null>(null);
  const [aiExplanation, setAiExplanation] = useState<string | null>(null);
  const [aiAdjustment, setAiAdjustment] = useState<string | null>(null);
  const [adjustmentText, setAdjustmentText] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function refreshState() {
    const [taskData, insightData] = await Promise.all([
      apiFetch<Task[]>("/tasks"),
      apiFetch<Insight>("/insights/today"),
    ]);
    setTasks(taskData);
    setInsight(insightData);
  }

  async function load() {
    try {
      await fetchMe();
      await refreshState();
    } catch (err) {
      setError(getErrorMessage(err, tErrors));
      router.push("/login");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  const todayStr = formatDateKey();
  const todayPlan = useMemo(() => {
    const items = sortByTime(
      tasks
        .filter((task) => task.deadline === todayStr)
        .map((task) => {
          const startValue = task.start_time ?? "00:00";
          const duration = task.estimated_duration ?? 30;
          return {
            id: task.id,
            label: task.title,
            start_time: `${todayStr}T${startValue}:00`,
            end_time: addMinutesToTime(todayStr, startValue, duration),
            status: task.status === "completed" ? "completed" : "planned",
            task_id: task.id,
          };
        })
    );

    return {
      id: `derived-${todayStr}`,
      plan_date: todayStr,
      status: items.length > 0 ? "derived" : "empty",
      source: "tasks",
      explanation: items.length > 0 ? "Today's schedule is derived from tasks." : null,
      items,
    };
  }, [tasks, todayStr]);

  async function generatePlan() {
    setGenerating(true);
    setBusyAction("generate");
    setError(null);
    router.push("/tasks?autoplan=1");
  }

  async function explainPlan() {
    if (!plan) return;
    setAiExplaining(true); setBusyAction("explain"); setError(null);
    try {
      const explanation = await apiFetch<{ daily_plan_id: string; explanation: string }>("/ai/explain", { method: "POST", body: JSON.stringify({ daily_plan_id: plan.id, question: "Why is this order?" }) });
      setAiExplanation(explanation.explanation);
    } catch (err) { setError(getErrorMessage(err, tErrors)); }
    finally { setAiExplaining(false); setBusyAction(null); }
  }

  async function adjustPlan() {
    if (!plan || !adjustmentText.trim()) return;
    setAiAdjusting(true); setBusyAction("adjust"); setError(null);
    try {
      const adjusted = await apiFetch<{ suggestion_id: string; explanation: string }>("/ai/adjust", { method: "POST", body: JSON.stringify({ daily_plan_id: plan.id, change_description: adjustmentText }) });
      setAiAdjustment(adjusted.explanation);
      await refreshState();
    } catch (err) { setError(getErrorMessage(err, tErrors)); }
    finally { setAiAdjusting(false); setBusyAction(null); }
  }

  async function progressTask(action: "complete" | "skip" | "delay" | "move", taskId: string) {
    setBusyAction("progress"); setError(null);
    try {
      const tomorrow = formatDateKey(new Date(Date.now() + 24 * 60 * 60 * 1000));
      const payload = action === "delay" ? { new_deadline: tomorrow, reason: "Deferred from today view" } : action === "move" ? { target_date: tomorrow, reason: "Moved from today view" } : { reason: "Updated from today view" };
      await apiFetch(`/progress/tasks/${taskId}/${action}`, { method: "POST", body: JSON.stringify(payload) });
      await refreshState();
    } catch (err) { setError(getErrorMessage(err, tErrors)); }
    finally { setBusyAction(null); }
  }

  const todayStrLabel = new Date().toLocaleDateString(locale === "vi" ? "vi-VN" : "en-US", { weekday: "long", month: "long", day: "numeric", year: "numeric" });
  const completionRate = insight && insight.total_tasks > 0 ? Math.round((insight.completed_tasks / insight.total_tasks) * 100) : 0;
  const greetingKey = getGreetingKey();
  const motivationKey = getMotivationKey();

  if (loading) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <FadeIn className="space-y-6">
          <LoadingState lines={2} variant="card" />
          <div className="grid gap-4 md:grid-cols-3"><LoadingState lines={1} variant="card" /><LoadingState lines={1} variant="card" /><LoadingState lines={1} variant="card" /></div>
          <LoadingState lines={4} variant="card" />
        </FadeIn>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <motion.div className="space-y-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>

        {/* ===== HERO ===== */}
        <motion.section
          className="relative overflow-hidden rounded-[32px] border border-border-light bg-gradient-to-br from-bg-warm via-white to-bg-soft px-6 py-8 shadow-card sm:px-10 sm:py-10"
          initial={{ opacity: 0, y: 20, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(255,122,92,0.06),transparent_40%),radial-gradient(circle_at_82%_20%,rgba(107,162,255,0.04),transparent_40%)]" />
          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-3">
              <motion.p className="section-label text-coral-500" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>{todayStrLabel}</motion.p>
              <motion.h1 className="font-display text-3xl font-bold tracking-tight text-neutral-900 sm:text-4xl lg:text-5xl" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                {tToday(`greeting.${greetingKey}`)}
              </motion.h1>
              <motion.p className="max-w-xl text-base leading-7 text-neutral-500" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                {tToday(`motivation.${motivationKey}`)}
              </motion.p>
              <motion.div className="flex flex-wrap items-center gap-2 pt-1" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>
                <span className="inline-flex items-center gap-1.5 rounded-pill bg-mint-50 px-3 py-1 text-xs font-medium text-mint-600">
                  <motion.span className="h-1.5 w-1.5 rounded-full bg-mint-400" animate={{ opacity: [1, 0.4, 1] }} transition={{ duration: 2, repeat: Infinity }} />
                  {tToday("aiReady")}
                </span>
                {todayPlan.items.length > 0 ? <Badge variant="coral" size="sm" dot>{tToday("dailyPlan")}: {todayPlan.items.length}</Badge> : null}
              </motion.div>
            </div>
            {insight ? (
              <motion.div className="flex items-center gap-4" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.4 }}>
                <ProgressRing progress={completionRate} size={100} strokeWidth={6} label={tToday("summary.complete")} />
              </motion.div>
            ) : null}
          </div>
        </motion.section>

        {/* Error */}
        <AnimatePresence>
          {error ? (
            <motion.div className="rounded-soft border border-coral-100 bg-coral-50 px-5 py-3" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
              <div className="flex items-center gap-3">
                <svg viewBox="0 0 20 20" className="h-4 w-4 shrink-0 fill-coral-500"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7 4a1 1 0 11-2 0 1 1 0 012 0zm-1-9a1 1 0 00-1 1v4a1 1 0 102 0V6a1 1 0 00-1-1z" clipRule="evenodd" /></svg>
                <p className="text-sm font-medium text-coral-700">{error}</p>
              </div>
            </motion.div>
          ) : null}
        </AnimatePresence>

        {/* ===== QUICK METRICS ===== */}
        <StaggerContainer className="grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <StaggerItem><StatCard label={tToday("planStatus")} value={todayPlan.items.length.toString()} hint={todayPlan.items.length ? tToday("itemsScheduled", { count: todayPlan.items.length.toString() }) : tToday("generateToBegin")} accent="coral" icon={<svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8]"><path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" /><circle cx="12" cy="12" r="4" /></svg>} /></StaggerItem>
          <StaggerItem><StatCard label={tToday("completedTotal")} value={insight ? `${insight.completed_tasks}/${insight.total_tasks}` : "0/0"} hint={insight ? `${completionRate}%` : tToday("noDataYet")} accent="mint" icon={<svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8]"><path d="M20 6L9 17l-5-5" /></svg>} /></StaggerItem>
          <StaggerItem><StatCard label={tToday("pendingTasks")} value={insight ? `${insight.pending_tasks}` : "0"} hint={insight ? insight.top_focus : tToday("waitingForData")} accent="sky" icon={<svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8]"><path d="M12 3v18" /><path d="M7 8c0-2.8 2.2-5 5-5s5 2.2 5 5c0 4-5 7-5 7s-5-3-5-7Z" /></svg>} /></StaggerItem>
          <StaggerItem><StatCard label={tToday("tasksRemaining")} value={insight ? `${insight.total_tasks - insight.completed_tasks}` : "0"} hint={insight ? tToday("skippedDeferred", { skipped: insight.skipped_tasks.toString(), deferred: insight.deferred_tasks.toString() }) : tToday("noData")} accent="lavender" icon={<svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8]"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></svg>} /></StaggerItem>
        </StaggerContainer>

        {/* ===== TIMELINE + AI (single column) ===== */}
        <Card variant="glass" className="p-6 sm:p-8">
            <SectionHeader
            eyebrow={tToday("dailyPlan")}
            title={todayPlan.items.length ? tToday("itemsScheduled", { count: todayPlan.items.length.toString() }) : tToday("noPlan")}
            description={todayPlan.items.length ? tToday("readyForToday") : tToday("noPlanDesc")}
            actions={
              <div className="flex flex-wrap gap-2">
                <Button onClick={generatePlan} disabled={generating || busyAction !== null} variant={plan ? "secondary" : "primary"} size="sm">
                  {generating ? tToday("generating") : plan ? tToday("regenerate") : tToday("generatePlan")}
                </Button>
                {plan ? <Button onClick={explainPlan} disabled={aiExplaining || busyAction !== null} variant="ghost" size="sm">{aiExplaining ? "..." : tToday("whyThisOrder")}</Button> : null}
              </div>
            }
          />

          {/* Timeline items */}
          {todayPlan.items.length ? (
            <div className="mt-6 space-y-1">
              {todayPlan.items.map((item, index) => {
                const isLast = index === todayPlan.items.length - 1;
                const itemStatus = item.status === "completed" ? "completed" : item.status === "in_progress" ? "active" : "pending";
                return (
                  <motion.div
                    key={item.id}
                    className="relative flex gap-4 group"
                    custom={index}
                    initial={{ opacity: 0, x: -15, scale: 0.97 }}
                    animate={{ opacity: 1, x: 0, scale: 1 }}
                    transition={{ delay: index * 0.08, duration: 0.4, ease: easeTimeline }}
                  >
                    <div className="flex flex-col items-center">
                      <div className={cn("relative z-10 flex h-6 w-6 shrink-0 items-center justify-center rounded-full border-2 transition-all duration-300", itemStatus === "completed" ? "border-mint-400 bg-mint-50" : itemStatus === "active" ? "border-coral-400 bg-coral-50" : "border-neutral-200 bg-white group-hover:border-neutral-300")}>
                        {itemStatus === "completed" ? (
                          <svg viewBox="0 0 12 12" className="h-3 w-3 fill-mint-500"><path d="M10.28 2.22a.75.75 0 010 1.06l-6 6a.75.75 0 01-1.06 0l-3-3a.75.75 0 011.06-1.06L3.75 7.69l5.47-5.47a.75.75 0 011.06 0z" /></svg>
                        ) : (
                          <span className={cn("h-2 w-2 rounded-full", itemStatus === "active" ? "bg-coral-400" : "bg-neutral-300")} />
                        )}
                      </div>
                      {!isLast ? <div className="h-full w-px bg-neutral-200 group-hover:bg-neutral-300 transition-colors" /> : null}
                    </div>
                    <div className={cn("mb-3 min-w-0 flex-1 rounded-2xl border bg-white/60 p-4 transition-all duration-200", itemStatus === "active" ? "border-coral-100 shadow-[0_0_0_1px_rgba(255,122,92,0.1)]" : "border-border-light hover:border-neutral-300 hover:shadow-sm")}>
                      <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                        <div className="min-w-0">
                          <div className="flex items-center gap-2">
                            <h3 className="text-sm font-semibold text-neutral-900 truncate">{item.label}</h3>
                            {itemStatus === "completed" ? <Badge variant="mint" size="sm">{tToday("done")}</Badge> : null}
                          </div>
                          <p className="mt-1 text-xs text-neutral-500">{formatTime(item.start_time, locale)} &mdash; {formatTime(item.end_time, locale)}</p>
                        </div>
                        {item.task_id ? (
                          <div className="flex shrink-0 flex-wrap gap-1.5">
                            <motion.button whileHover={{ y: -1 }} whileTap={{ scale: 0.95 }} onClick={() => progressTask("complete", item.task_id!)} disabled={busyAction === "progress"} className="rounded-pill bg-mint-50 px-2.5 sm:px-3 py-1.5 text-[11px] sm:text-xs font-medium text-mint-600 transition-colors hover:bg-mint-100 disabled:opacity-50">{tToday("complete")}</motion.button>
                            <motion.button whileHover={{ y: -1 }} whileTap={{ scale: 0.95 }} onClick={() => progressTask("delay", item.task_id!)} disabled={busyAction === "progress"} className="rounded-pill bg-neutral-50 px-2.5 sm:px-3 py-1.5 text-[11px] sm:text-xs font-medium text-neutral-600 transition-colors hover:bg-neutral-100 disabled:opacity-50">{tToday("delay")}</motion.button>
                            <motion.button whileHover={{ y: -1 }} whileTap={{ scale: 0.95 }} onClick={() => progressTask("skip", item.task_id!)} disabled={busyAction === "progress"} className="rounded-pill bg-neutral-50 px-2.5 sm:px-3 py-1.5 text-[11px] sm:text-xs font-medium text-neutral-600 transition-colors hover:bg-neutral-100 disabled:opacity-50">{tToday("skip")}</motion.button>
                            <motion.button whileHover={{ y: -1 }} whileTap={{ scale: 0.95 }} onClick={() => progressTask("move", item.task_id!)} disabled={busyAction === "progress"} className="rounded-pill bg-neutral-50 px-2.5 sm:px-3 py-1.5 text-[11px] sm:text-xs font-medium text-neutral-600 transition-colors hover:bg-neutral-100 disabled:opacity-50">{tToday("move")}</motion.button>
                          </div>
                        ) : null}
                      </div>
                    </div>
                  </motion.div>
                );
              })}
            </div>
          ) : (
            <FadeInUp className="mt-6">
              <EmptyState illustration="plan" title={plan ? tToday("planEmpty") : tToday("noPlan")} description={plan ? tToday("planEmptyDesc") : tToday("noPlanDesc")} actionLabel={plan ? undefined : tToday("generatePlan")} onActionClick={generatePlan} />
            </FadeInUp>
          )}
        </Card>

        {/* ===== AI EXPLANATION ===== */}
        <AnimatePresence>
          {aiExplanation ? (
            <motion.div key="ai-explanation" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }} transition={{ duration: 0.4 }}>
              <Card variant="glass" className="p-6">
                <div className="flex items-start gap-4">
                  <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-sky-50 text-sky-400">
                    <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="9" /><path d="M12 16v-4M12 8h.01" /></svg>
                  </div>
                  <div className="space-y-2">
                    <SectionHeader eyebrow={tToday("aiExplanation")} title={tToday("whyThisOrderTitle")} />
                    <p className="text-sm leading-6 text-neutral-500">{aiExplanation}</p>
                  </div>
                </div>
              </Card>
            </motion.div>
          ) : null}
        </AnimatePresence>

        {/* ===== AI ADJUSTMENT ===== */}
        <Card variant="glass" className="p-6 sm:p-8">
          <SectionHeader eyebrow={tToday("aiAssistant")} title={tToday("adjustTitle")} description={tToday("adjustDesc")} />
          <div className="mt-4 space-y-3">
            <Input placeholder={tToday("aiAdjustPlaceholder")} value={adjustmentText} onChange={(event) => setAdjustmentText(event.target.value)} />
            <div className="flex items-center gap-3">
              <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.98 }}>
                <Button onClick={adjustPlan} disabled={!plan || aiAdjusting || !adjustmentText.trim() || busyAction !== null} size="sm">
                  {aiAdjusting ? tToday("aiAdjusting") : tToday("aiAdjust")}
                </Button>
              </motion.div>
              {aiAdjusting ? (
                <motion.span className="flex items-center gap-2 text-xs text-neutral-500" initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
                  <motion.span className="h-1.5 w-1.5 rounded-full bg-coral-400" animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.5, repeat: Infinity }} />
                  {tToday("aiThinking")}
                </motion.span>
              ) : null}
            </div>
            <AnimatePresence>
              {aiAdjustment ? (
                <motion.div key="ai-adjustment" className="rounded-soft border border-sky-100 bg-sky-50 px-4 py-3 text-sm text-sky-700" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} exit={{ opacity: 0 }}>
                  <div className="flex items-start gap-3">
                    <svg viewBox="0 0 20 20" className="mt-0.5 h-4 w-4 shrink-0 fill-sky-400"><path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" /></svg>
                    <span>{aiAdjustment}</span>
                  </div>
                </motion.div>
              ) : null}
            </AnimatePresence>
          </div>
        </Card>

        {/* ===== INSIGHT + TASK QUEUE in grid ===== */}
        <div className="grid gap-8 lg:grid-cols-[1.3fr_0.7fr]">
          {/* Task queue */}
          <div className="space-y-4">
            <div className="flex items-center justify-between">
              <p className="section-label">{tToday("inBacklog", { count: tasks.length.toString() })}</p>
              <Link href="/tasks/new" className="text-xs font-medium text-coral-500 hover:text-coral-600">
                <span className="inline-flex items-center gap-1">
                  <svg viewBox="0 0 24 24" className="h-3 w-3 fill-none stroke-current stroke-[1.8]"><path d="M12 5v14M5 12h14" /></svg>
                  New
                </span>
              </Link>
            </div>
            <div className="space-y-2">
              {tasks
                .filter((t) => t.status !== "completed")
                .sort((a, b) => {
                  if (!a.start_time && !b.start_time) return 0;
                  if (!a.start_time) return 1;
                  if (!b.start_time) return -1;
                  return a.start_time.localeCompare(b.start_time);
                })
                .slice(0, 8)
                .map((task, i) => (
                <motion.div
                  key={task.id}
                  className="flex items-center gap-3 rounded-soft border border-border-light bg-white/60 p-3 transition-all hover:border-neutral-300"
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: i * 0.04 }}
                >
                  <div className={cn("h-1.5 w-1.5 shrink-0 rounded-full", task.priority === "urgent" ? "bg-coral-400" : "bg-neutral-300")} />
                  <span className="flex-1 text-sm text-neutral-700 truncate">{task.title}</span>
                  {task.start_time && <span className="text-xs text-neutral-400">{task.start_time}</span>}
                  {task.priority ? <Badge variant={task.priority === "urgent" ? "coral" : "neutral"} size="sm">{task.priority}</Badge> : null}
                </motion.div>
              ))}
            </div>
          </div>

          {/* Daily Insight */}
          {insight ? (
            <motion.div variants={scaleIn} initial="hidden" animate="visible">
              <Card variant="glass" className="p-6">
                <SectionHeader eyebrow={tToday("insight")} title={tToday("summary.prefix")} description={insight.top_focus} />
                <motion.div className="mt-6 flex justify-center" initial={{ scale: 0.9, opacity: 0 }} animate={{ scale: 1, opacity: 1 }} transition={{ delay: 0.3 }}>
                  <ProgressRing progress={completionRate} size={130} strokeWidth={8} label={tToday("summary.complete")} sublabel={`${insight.completed_tasks} ${tToday("completeSuffix")}`} />
                </motion.div>
                <div className="mt-6 grid grid-cols-2 gap-3">
                  {[
                    { label: tToday("summary.completed"), value: insight.completed_tasks, color: "text-mint-500" },
                    { label: tToday("summary.pending"), value: insight.pending_tasks, color: "text-sky-400" },
                    { label: tToday("summary.skipped"), value: insight.skipped_tasks, color: "text-neutral-500" },
                    { label: tToday("summary.deferred"), value: insight.deferred_tasks, color: "text-lavender-400" },
                  ].map((item, i) => (
                    <motion.div key={item.label} className="rounded-soft border border-border-light bg-white/60 p-3 text-center" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 + i * 0.08 }}>
                      <p className="text-xs text-neutral-400">{item.label}</p>
                      <p className={`mt-1 font-display text-xl font-semibold ${item.color}`}>{item.value}</p>
                    </motion.div>
                  ))}
                </div>
                {insight.highlights.length > 0 ? (
                  <div className="mt-6 space-y-2">
                    <p className="section-label">{tToday("summary.highlights")}</p>
                    {insight.highlights.map((item, i) => (
                      <motion.div key={item} className="rounded-soft border border-border-light bg-white/60 px-4 py-3 text-sm text-neutral-600" initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: 0.6 + i * 0.1 }}>
                        <div className="flex items-start gap-2">
                          <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-coral-300" />
                          <span>{item}</span>
                        </div>
                      </motion.div>
                    ))}
                  </div>
                ) : null}
              </Card>
            </motion.div>
          ) : (
            <Card variant="glass" className="p-6">
              <EmptyState illustration="insight" title={tToday("insightNone")} description={tToday("insightNoneDesc")} />
            </Card>
          )}
        </div>
      </motion.div>
    </main>
  );
}
