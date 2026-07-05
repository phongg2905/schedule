"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { motion } from "framer-motion";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { ProgressRing } from "@/components/ui/progress-ring";
import { LoadingState } from "@/components/ui/loading-state";
import { apiFetch } from "@/services/api";
import { fetchMe } from "@/services/auth";
import { useAppIntl } from "@/providers/intl-provider";
import { cn } from "@/lib/cn";
import { sortByTime } from "@/lib/sort";
import {
  FadeInUp,
  FadeInDown,
  StaggerContainer,
  StaggerItem,
  scaleIn,
} from "@/lib/motion";

// ── Types ──

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

function getGreetingKey(): string {
  const hour = new Date().getHours();
  if (hour < 12) return "morning";
  if (hour < 17) return "afternoon";
  return "evening";
}

function getMotivationKey(): string {
  return `${new Date().getDate() % 6}`;
}

function getTodayDateStr(locale: string): string {
  return new Date().toLocaleDateString(locale === "vi" ? "vi-VN" : "en-US", {
    weekday: "long",
    month: "long",
    day: "numeric",
    year: "numeric",
  });
}

export default function HomePage() {
  const router = useRouter();
  const tHome = useTranslations("home");
  const tTasks = useTranslations("tasks");
  const tToday = useTranslations("today");
  const { isAuthenticated, locale } = useAppIntl();

  const [user, setUser] = useState<{ name: string } | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [insight, setInsight] = useState<Insight | null>(null);
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const me = await fetchMe();
      setUser(me);
      const [taskData, planData, insightData] = await Promise.all([
        apiFetch<Task[]>("/tasks").catch(() => [] as Task[]),
        apiFetch<DailyPlan | null>("/daily-plans/today").catch(() => null),
        apiFetch<Insight>("/insights/today").catch(() => null),
      ]);
      setTasks(taskData);
      setPlan(planData);
      setInsight(insightData);
    } catch {
      // Not authenticated — show landing page
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => { void load(); }, []);

  const greetingKey = getGreetingKey();
  const motivationKey = getMotivationKey();

  // ── Landing page (not authenticated) ──
  if (!isAuthenticated && !loading) {
    const features = [
      {
        titleKey: "flow",
        descKey: "flowDesc",
        gradient: "from-coral-50 to-coral-100",
        icon: (
          <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8] text-coral-500">
            <path d="M12 2v4" /><path d="M12 18v4" /><path d="M4.93 4.93l2.83 2.83" /><path d="M16.24 16.24l2.83 2.83" /><path d="M2 12h4" /><path d="M18 12h4" /><circle cx="12" cy="12" r="4" />
          </svg>
        ),
      },
      {
        titleKey: "focus",
        descKey: "focusDesc",
        gradient: "from-sky-50 to-sky-100",
        icon: (
          <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8] text-sky-400">
            <path d="M12 3c.132 0 .263 0 .393 0a7.5 7.5 0 007.92 12.446A9 9 0 1112 2.992z" />
          </svg>
        ),
      },
      {
        titleKey: "progress",
        descKey: "progressDesc",
        gradient: "from-lavender-50 to-lavender-100",
        icon: (
          <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8] text-lavender-400">
            <path d="M22 12h-4l-3 9L9 3l-3 9H2" />
          </svg>
        ),
      },
    ];

    return (
      <div className="relative min-h-screen">
        <section className="relative mx-auto flex min-h-[calc(100vh-4rem)] max-w-7xl flex-col items-center justify-center px-4 pt-20 sm:px-6 lg:px-8">
          <FadeInDown>
            <span className="inline-flex items-center gap-2 rounded-pill border border-coral-100 bg-coral-50/60 px-4 py-2 text-xs font-semibold tracking-wider text-coral-500 backdrop-blur-sm">
              <span className="h-1.5 w-1.5 rounded-full bg-coral-400" />
              {tHome("badge")}
            </span>
          </FadeInDown>

          <FadeInUp delay={0.1}>
            <div className="max-w-3xl text-center">
              <h1 className="font-display text-4xl font-bold tracking-tight text-neutral-900 sm:text-5xl lg:text-6xl">
                {tHome.rich("title", {
                  accent: () => (
                    <span className="bg-gradient-to-r from-coral-400 to-coral-600 bg-clip-text text-transparent">
                      {tHome("titleAccent")}
                    </span>
                  ),
                })}
              </h1>
              <p className="mx-auto mt-6 max-w-xl text-lg leading-7 text-neutral-500">{tHome("description")}</p>
            </div>
          </FadeInUp>

          <FadeInUp delay={0.2}>
            <div className="mt-8 flex flex-wrap items-center justify-center gap-4">
              <Link href="/register"><Button variant="primary" size="lg" className="shadow-button-primary">{tHome("cta")}</Button></Link>
              <Link href="/login"><Button variant="secondary" size="lg">{tHome("signIn")}</Button></Link>
            </div>
          </FadeInUp>

          <StaggerContainer className="mt-16 grid w-full max-w-4xl gap-4 sm:grid-cols-3">
            {features.map((feature) => (
              <StaggerItem key={feature.titleKey}>
                <Card variant="ambient" className="group p-6 text-center transition-all duration-300 hover:-translate-y-1 hover:shadow-card-hover">
                  <div className={cn("mx-auto mb-4 flex h-12 w-12 items-center justify-center rounded-2xl bg-gradient-to-br transition-transform duration-300 group-hover:scale-110", feature.gradient)}>
                    {feature.icon}
                  </div>
                  <h3 className="mb-2 font-display text-lg font-semibold text-neutral-900">{tHome(`features.${feature.titleKey}`)}</h3>
                  <p className="text-sm leading-6 text-neutral-500">{tHome(`features.${feature.descKey}`)}</p>
                </Card>
              </StaggerItem>
            ))}
          </StaggerContainer>

          <motion.div className="mt-16 text-neutral-300" animate={{ y: [0, 8, 0] }} transition={{ duration: 2.5, repeat: Infinity, ease: "easeInOut" }}>
            <svg viewBox="0 0 24 24" className="h-6 w-6 fill-none stroke-current stroke-[1.5]"><path d="M12 5v14M5 12l7 7 7-7" /></svg>
          </motion.div>
        </section>
        <div className="h-32 bg-gradient-to-b from-transparent to-bg-soft" />
      </div>
    );
  }

  // ── Loading state (authenticated) ──
  if (loading) {
    return (
      <main className="mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8">
        <div className="space-y-6">
          <LoadingState lines={2} variant="card" />
          <div className="grid gap-4 md:grid-cols-3"><LoadingState lines={1} variant="card" /><LoadingState lines={1} variant="card" /><LoadingState lines={1} variant="card" /></div>
        </div>
      </main>
    );
  }

  // ── Dashboard (authenticated) ──
  const todayTasks = sortByTime(tasks.filter((t) => t.deadline && t.deadline <= new Date().toISOString().slice(0, 10) && t.status !== "completed")).slice(0, 3);
  const tomorrowDate = new Date(Date.now() + 24 * 60 * 60 * 1000).toISOString().slice(0, 10);
  const tomorrowTasks = sortByTime(tasks.filter((t) => t.deadline && t.deadline === tomorrowDate && t.status !== "completed")).slice(0, 3);
  const completionRate = insight && insight.total_tasks > 0 ? Math.round((insight.completed_tasks / insight.total_tasks) * 100) : 0;

  return (
    <main className="mx-auto max-w-7xl px-4 py-6 sm:px-6 lg:px-8">
      <motion.div className="space-y-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
        
        {/* ── Hero Section ── */}
        <motion.section
          className="relative overflow-hidden rounded-[32px] border border-border-light bg-gradient-to-br from-bg-warm via-white to-bg-soft px-6 py-8 shadow-card sm:px-10 sm:py-10"
          initial={{ opacity: 0, y: 20, scale: 0.98 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          transition={{ duration: 0.5 }}
        >
          <div className="pointer-events-none absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(255,122,92,0.06),transparent_40%),radial-gradient(circle_at_82%_20%,rgba(107,162,255,0.04),transparent_40%)]" />
          <div className="relative flex flex-col gap-6 lg:flex-row lg:items-center lg:justify-between">
            <div className="space-y-3">
              <motion.p className="section-label text-coral-500" initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
                {getTodayDateStr(locale)}
              </motion.p>
              <motion.h1 className="font-display text-3xl font-bold tracking-tight text-neutral-900 sm:text-4xl" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
                {tHome(`dashboard.greeting_${greetingKey}`)}{user ? `, ${user.name.split(" ")[0]}` : ""}
              </motion.h1>
              <motion.p className="max-w-xl text-base leading-7 text-neutral-500" initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3 }}>
                {tHome(`dashboard.motivation_${motivationKey}`)}
              </motion.p>
              <motion.div className="flex flex-wrap items-center gap-2 pt-1" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }}>
                <span className="inline-flex items-center gap-1.5 rounded-pill bg-mint-50 px-3 py-1 text-xs font-medium text-mint-600">
                  <motion.span className="h-1.5 w-1.5 rounded-full bg-mint-400" animate={{ opacity: [1, 0.4, 1] }} transition={{ duration: 2, repeat: Infinity }} />
                  {tHome("dashboard.aiReady")}
                </span>
                {plan ? <Badge variant="coral" size="sm" dot>{plan.status}</Badge> : null}
              </motion.div>
            </div>
            {insight ? (
              <motion.div className="flex items-center gap-4" initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }} transition={{ delay: 0.4 }}>
                <ProgressRing progress={completionRate} size={90} strokeWidth={5} label={tHome("dashboard.todayProgress")} />
              </motion.div>
            ) : null}
          </div>
        </motion.section>

        {/* ── Quick Actions ── */}
        <motion.div className="flex flex-wrap gap-2 sm:gap-3" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
          <Link href="/tasks/new">
            <motion.div whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }}>
              <Button variant="primary" size="md">
                <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><path d="M12 5v14M5 12h14" /></svg>
                {tHome("dashboard.createTask")}
              </Button>
            </motion.div>
          </Link>
          <Link href="/today">
            <motion.div whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }}>
              <Button variant="secondary" size="md">
                <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></svg>
                {tHome("dashboard.generatePlan")}
              </Button>
            </motion.div>
          </Link>
          <Link href="/tasks">
            <motion.div whileHover={{ y: -2 }} whileTap={{ scale: 0.98 }}>
              <Button variant="ghost" size="md">
                <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></svg>
                {tHome("dashboard.openTasks")}
              </Button>
            </motion.div>
          </Link>
        </motion.div>

        {/* ── Main Grid ── */}
        <div className="grid gap-6 lg:grid-cols-[1.4fr_0.6fr]">
          {/* Left column */}
          <div className="space-y-6">
            {/* Today's Focus */}
            <motion.div variants={scaleIn} initial="hidden" animate="visible" transition={{ delay: 0.15 }}>
              <Card variant="glass" className="p-6 sm:p-8">
                <div className="mb-4 flex items-start justify-between gap-4">
                  <div>
                    <p className="section-label">{tHome("dashboard.todaysFocus")}</p>
                    <p className="mt-0.5 text-sm text-neutral-500">{tHome("dashboard.todaysFocusDesc")}</p>
                  </div>
                  {plan ? (
                    <Badge variant="mint" size="sm" dot>{tHome("dashboard.scheduledCount", { count: plan.items?.length || 0 })}</Badge>
                  ) : null}
                </div>
                {plan?.items?.length ? (
                  <div className="space-y-2">
                    {plan.items.slice(0, 3).map((item, i) => (
                      <motion.div
                        key={item.id}
                        className="flex items-center gap-3 rounded-soft border border-border-light bg-white/60 p-3 transition-all hover:border-neutral-300"
                        initial={{ opacity: 0, x: -10 }}
                        animate={{ opacity: 1, x: 0 }}
                        transition={{ delay: 0.3 + i * 0.08 }}
                      >
                        <div className={cn("h-2 w-2 rounded-full", i === 0 ? "bg-coral-400" : "bg-neutral-300")} />
                        <div className="flex-1 min-w-0">
                          <p className="text-sm font-medium text-neutral-900 truncate">{item.label}</p>
                          <p className="text-xs text-neutral-500">{item.start_time?.slice(11, 16)} &mdash; {item.end_time?.slice(11, 16)}</p>
                        </div>
                        {i === 0 ? <span className="text-[10px] font-semibold uppercase tracking-wider text-coral-500">{tHome("dashboard.next")}</span> : null}
                      </motion.div>
                    ))}
                    {plan.items.length > 3 ? (
                      <Link href="/today" className="block text-center text-xs font-medium text-coral-500 hover:text-coral-600 pt-2">
                        +{plan.items.length - 3} more items &rarr;
                      </Link>
                    ) : null}
                  </div>
                ) : (
                  <div className="rounded-soft border border-border-light bg-white/50 px-5 py-8 text-center">
                    <div className="mx-auto mb-2 flex h-10 w-10 items-center justify-center rounded-2xl bg-neutral-100 text-neutral-400">
                      <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></svg>
                    </div>
                    <p className="text-sm font-medium text-neutral-600">{tHome("dashboard.noFocusYet")}</p>
                    <Link href="/today"><Button variant="soft" size="sm" className="mt-3">{tHome("dashboard.startPlanning")}</Button></Link>
                  </div>
                )}
              </Card>
            </motion.div>

            {/* Upcoming */}
            <motion.div variants={scaleIn} initial="hidden" animate="visible" transition={{ delay: 0.2 }}>
              <Card variant="glass" className="p-6 sm:p-8">
                <div className="mb-4 flex items-center justify-between">
                  <div>
                    <p className="section-label">{tHome("dashboard.upcoming")}</p>
                  </div>
                  <Link href="/tasks" className="text-xs font-medium text-coral-500 hover:text-coral-600">{tHome("dashboard.viewAll")}</Link>
                </div>
                <div className="grid gap-4 sm:grid-cols-2">
                  <div>
                    <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-neutral-400">{tHome("dashboard.tomorrow")}</p>
                    {tomorrowTasks.length > 0 ? (
                      <div className="space-y-1.5">
                        {tomorrowTasks.map((task) => (
                          <div key={task.id} className="flex items-center gap-2 rounded-soft border border-border-light bg-white/60 px-3 py-2">
                            <div className="h-1.5 w-1.5 shrink-0 rounded-full bg-sky-300" />
                            <span className="text-sm text-neutral-700 truncate">{task.title}</span>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <p className="text-sm text-neutral-400">{tHome("dashboard.noUpcoming")}</p>
                    )}
                  </div>
                  <div>
                    <p className="mb-2 text-[11px] font-semibold uppercase tracking-wider text-neutral-400">{tHome("dashboard.nextWeek")}</p>
                    <p className="text-sm text-neutral-400">{tHome("dashboard.noUpcoming")}</p>
                  </div>
                </div>
              </Card>
            </motion.div>

            {/* AI Insights */}
            {insight ? (
              <motion.div variants={scaleIn} initial="hidden" animate="visible" transition={{ delay: 0.25 }}>
                <Card variant="glass" className="p-6 sm:p-8">
                  <div className="mb-4">
                    <p className="section-label">{tHome("dashboard.aiInsights")}</p>
                    <p className="mt-0.5 text-sm text-neutral-500">{tHome("dashboard.aiInsightsDesc")}</p>
                  </div>
                  <div className="rounded-soft border border-sky-50 bg-sky-50/50 p-4">
                    <p className="text-sm font-medium text-sky-700">{insight.top_focus}</p>
                    {insight.highlights.length > 0 ? (
                      <ul className="mt-2 space-y-1">
                        {insight.highlights.slice(0, 2).map((h, i) => (
                          <li key={i} className="flex items-start gap-2 text-sm text-sky-600">
                            <span className="mt-1 h-1.5 w-1.5 shrink-0 rounded-full bg-sky-400" />
                            {h}
                          </li>
                        ))}
                      </ul>
                    ) : null}
                  </div>
                </Card>
              </motion.div>
            ) : (
              <motion.div variants={scaleIn} initial="hidden" animate="visible" transition={{ delay: 0.25 }}>
                <Card variant="glass" className="p-6 sm:p-8">
                  <p className="section-label">{tHome("dashboard.aiInsights")}</p>
                  <p className="mt-1 text-sm text-neutral-500">{tHome("dashboard.noInsightsYet")}</p>
                </Card>
              </motion.div>
            )}
          </div>

          {/* Right column */}
          <div className="space-y-6">
            {/* Progress */}
            <motion.div variants={scaleIn} initial="hidden" animate="visible" transition={{ delay: 0.2 }}>
              <Card variant="glass" className="p-6">
                <p className="section-label mb-4">{tHome("dashboard.progress")}</p>
                <StaggerContainer className="space-y-3">
                  <StaggerItem>
                    <div className="rounded-soft border border-border-light bg-white/60 p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-neutral-700">{tHome("dashboard.todayProgress")}</span>
                        <span className="text-sm font-semibold text-neutral-900">{completionRate}%</span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-neutral-100">
                        <motion.div
                          className="h-full rounded-full bg-mint-400"
                          initial={{ width: 0 }}
                          animate={{ width: `${completionRate}%` }}
                          transition={{ duration: 1, delay: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
                        />
                      </div>
                    </div>
                  </StaggerItem>
                  <StaggerItem>
                    <div className="rounded-soft border border-border-light bg-white/60 p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-neutral-700">{tHome("dashboard.weekProgress")}</span>
                        <span className="text-sm font-semibold text-neutral-900">--</span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-neutral-100">
                        <div className="h-full w-0 rounded-full bg-sky-300" />
                      </div>
                    </div>
                  </StaggerItem>
                  <StaggerItem>
                    <div className="rounded-soft border border-border-light bg-white/60 p-4">
                      <div className="flex items-center justify-between mb-2">
                        <span className="text-sm font-medium text-neutral-700">{tHome("dashboard.monthProgress")}</span>
                        <span className="text-sm font-semibold text-neutral-900">--</span>
                      </div>
                      <div className="h-1.5 w-full overflow-hidden rounded-full bg-neutral-100">
                        <div className="h-full w-0 rounded-full bg-lavender-300" />
                      </div>
                    </div>
                  </StaggerItem>
                </StaggerContainer>
              </Card>
            </motion.div>

            {/* Quick stats */}
            <motion.div variants={scaleIn} initial="hidden" animate="visible" transition={{ delay: 0.3 }}>
              <Card variant="glass" className="p-6">
                <p className="section-label mb-3">{tTasks("page.title")}</p>
                <div className="space-y-2">
                  {todayTasks.length > 0 ? (
                    todayTasks.map((task) => (
                      <div key={task.id} className="flex items-center gap-2 rounded-soft border border-border-light bg-white/60 px-3 py-2">
                        <div className={cn("h-1.5 w-1.5 shrink-0 rounded-full", task.priority === "urgent" ? "bg-coral-400" : "bg-neutral-300")} />
                        <span className="flex-1 text-sm text-neutral-700 truncate">{task.title}</span>
                        {task.priority ? <Badge variant={task.priority === "urgent" ? "coral" : "neutral"} size="sm">{tTasks(`priority.${task.priority}`)}</Badge> : null}
                      </div>
                    ))
                  ) : (
                    <p className="text-sm text-neutral-400 text-center py-3">{tHome("dashboard.noFocusYet")}</p>
                  )}
                </div>
                {tasks.length > 3 ? (
                  <Link href="/tasks" className="block text-center text-xs font-medium text-coral-500 hover:text-coral-600 mt-3">
                    +{tasks.length - 3} more tasks &rarr;
                  </Link>
                ) : null}
              </Card>
            </motion.div>
          </div>
        </div>
      </motion.div>
    </main>
  );
}
