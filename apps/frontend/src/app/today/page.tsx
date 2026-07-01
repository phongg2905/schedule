"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/services/api";
import { fetchMe } from "@/services/auth";
import { TaskCreateForm, TaskList } from "@/features/tasks";

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

export default function TodayPage() {
  const router = useRouter();
  const [plan, setPlan] = useState<DailyPlan | null>(null);
  const [tasks, setTasks] = useState<Task[]>([]);
  const [insight, setInsight] = useState<Insight | null>(null);
  const [loading, setLoading] = useState(true);
  const [generating, setGenerating] = useState(false);
  const [aiGenerating, setAiGenerating] = useState(false);
  const [aiExplaining, setAiExplaining] = useState(false);
  const [aiAdjusting, setAiAdjusting] = useState(false);
  const [busyAction, setBusyAction] = useState<"generate" | "ai-generate" | "explain" | "adjust" | "progress" | null>(null);
  const [aiExplanation, setAiExplanation] = useState<string | null>(null);
  const [aiAdjustment, setAiAdjustment] = useState<string | null>(null);
  const [adjustmentText, setAdjustmentText] = useState("");
  const [error, setError] = useState<string | null>(null);

  async function refreshState() {
    const [planData, taskData, insightData] = await Promise.all([
      apiFetch<DailyPlan | null>("/daily-plans/today"),
      apiFetch<Task[]>("/tasks"),
      apiFetch<Insight>("/insights/today"),
    ]);
    setPlan(planData);
    setTasks(taskData);
    setInsight(insightData);
  }

  async function load() {
    try {
      await fetchMe();
      await refreshState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load today");
      router.push("/login");
    } finally {
      setLoading(false);
    }
  }

  useEffect(() => {
    void load();
  }, []);

  async function handleTaskCreated() {
    await fetchMe();
    await refreshState();
  }

  async function generatePlan() {
    setGenerating(true);
    setBusyAction("generate");
    setError(null);
    try {
      const planDate = new Date().toLocaleDateString("en-CA");
      await apiFetch<DailyPlan>("/daily-plans/generate", {
        method: "POST",
        body: JSON.stringify({
          plan_date: planDate,
          context_window_type: "rule_based_daily_plan",
          trigger_source: "manual",
        }),
      });
      await refreshState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate plan");
    } finally {
      setGenerating(false);
      setBusyAction(null);
    }
  }

  async function generateAiPlan() {
    setAiGenerating(true);
    setBusyAction("ai-generate");
    setError(null);
    try {
      const planDate = new Date().toLocaleDateString("en-CA");
      const generated = await apiFetch<DailyPlan>("/ai/generate-daily-plan", {
        method: "POST",
        body: JSON.stringify({
          plan_date: planDate,
          context_window_type: "ai_generation",
          trigger_source: "manual",
        }),
      });
      setPlan(generated);
      setAiExplanation(generated.explanation ?? null);
      await refreshState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to generate AI plan");
    } finally {
      setAiGenerating(false);
      setBusyAction(null);
    }
  }

  async function explainPlan() {
    if (!plan) {
      return;
    }
    setAiExplaining(true);
    setBusyAction("explain");
    setError(null);
    try {
      const explanation = await apiFetch<{ daily_plan_id: string; explanation: string }>("/ai/explain", {
        method: "POST",
        body: JSON.stringify({
          daily_plan_id: plan.id,
          question: "Why is this order?",
        }),
      });
      setAiExplanation(explanation.explanation);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to explain plan");
    } finally {
      setAiExplaining(false);
      setBusyAction(null);
    }
  }

  async function adjustPlan() {
    if (!plan || !adjustmentText.trim()) {
      return;
    }
    setAiAdjusting(true);
    setBusyAction("adjust");
    setError(null);
    try {
      const adjusted = await apiFetch<{ suggestion_id: string; explanation: string }>("/ai/adjust", {
        method: "POST",
        body: JSON.stringify({
          daily_plan_id: plan.id,
          change_description: adjustmentText,
        }),
      });
      setAiAdjustment(adjusted.explanation);
      await refreshState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to adjust plan");
    } finally {
      setAiAdjusting(false);
      setBusyAction(null);
    }
  }

  async function progressTask(action: "complete" | "skip" | "delay" | "move", taskId: string) {
    setBusyAction("progress");
    setError(null);
    try {
      const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000).toLocaleDateString("en-CA");
      const payload =
        action === "delay"
          ? { new_deadline: tomorrow, reason: "Deferred from today view" }
          : action === "move"
            ? { target_date: tomorrow, reason: "Moved from today view" }
            : { reason: "Updated from today view" };
      await apiFetch(`/progress/tasks/${taskId}/${action}`, {
        method: "POST",
        body: JSON.stringify(payload),
      });
      await refreshState();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to update task progress");
    } finally {
      setBusyAction(null);
    }
  }

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <section className="rounded-[28px] border border-[var(--border)] bg-[var(--surface)] p-8 shadow-soft backdrop-blur">
        <div className="flex flex-col gap-2 md:flex-row md:items-end md:justify-between">
          <div>
            <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Today</p>
            <h1 className="text-3xl font-semibold tracking-tight text-ink-900">What needs your attention today?</h1>
          </div>
          <p className="text-sm text-slate-600">Phase 6 core flow: plan, progress, adjust, and learn.</p>
        </div>
        {loading ? <p className="mt-6 text-slate-600">Loading...</p> : null}
        {error ? <p className="mt-6 text-sm text-red-600">{error}</p> : null}
        {!loading ? (
          <div className="mt-6 grid gap-6 lg:grid-cols-[1.2fr_0.8fr]">
            <div className="space-y-4">
              <div className="rounded-3xl border border-[var(--border)] bg-white/80 p-5">
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Daily plan</p>
                    <h2 className="mt-2 text-xl font-semibold text-ink-900">{plan ? plan.plan_date : "No plan yet"}</h2>
                  </div>
                  <button onClick={generatePlan} disabled={generating || busyAction !== null} className="rounded-full border border-black/10 px-4 py-2 text-xs font-medium text-ink-900 disabled:opacity-50">
                    {generating ? "Generating..." : plan ? "Regenerate" : "Generate today"}
                  </button>
                </div>
                <p className="mt-2 text-sm text-slate-600">{plan?.explanation ?? "Rule-based planning is available once you generate today."}</p>
                <div className="mt-3 flex flex-wrap gap-2">
                  <button onClick={generateAiPlan} disabled={aiGenerating || busyAction !== null} className="rounded-full border border-black/10 px-4 py-2 text-xs font-medium text-ink-900 disabled:opacity-50">
                    {aiGenerating ? "AI generating..." : "Generate with AI"}
                  </button>
                  <button onClick={explainPlan} disabled={!plan || aiExplaining || busyAction !== null} className="rounded-full border border-black/10 px-4 py-2 text-xs font-medium text-ink-900 disabled:opacity-50">
                    {aiExplaining ? "Explaining..." : "Why this order?"}
                  </button>
                </div>
                <div className="mt-4 grid gap-3 rounded-2xl border border-[var(--border)] bg-[rgba(247,247,242,0.7)] p-4">
                  <p className="text-xs uppercase tracking-[0.18em] text-slate-500">AI adjustment</p>
                  <input
                    className="w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3 text-sm"
                    placeholder="Example: I have a meeting at 15:00, reschedule the afternoon block."
                    value={adjustmentText}
                    onChange={(event) => setAdjustmentText(event.target.value)}
                  />
                  <button onClick={adjustPlan} disabled={!plan || aiAdjusting || !adjustmentText.trim() || busyAction !== null} className="w-fit rounded-full border border-black/10 px-4 py-2 text-xs font-medium text-ink-900 disabled:opacity-50">
                    {aiAdjusting ? "Adjusting..." : "Ask AI to adjust"}
                  </button>
                </div>
                {aiExplanation ? (
                  <div className="mt-4 rounded-2xl border border-[var(--border)] bg-[rgba(247,247,242,0.7)] p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">AI explanation</p>
                    <p className="mt-2 text-sm text-slate-700">{aiExplanation}</p>
                  </div>
                ) : null}
                {aiAdjustment ? (
                  <div className="mt-4 rounded-2xl border border-[var(--border)] bg-[rgba(247,247,242,0.7)] p-4">
                    <p className="text-xs uppercase tracking-[0.18em] text-slate-500">AI adjustment</p>
                    <p className="mt-2 text-sm text-slate-700">{aiAdjustment}</p>
                  </div>
                ) : null}
                {plan?.items?.length ? (
                  <div className="mt-4 space-y-2">
                    {plan.items.map((item) => (
                      <div key={item.id} className="rounded-2xl border border-black/5 bg-[rgba(247,247,242,0.7)] p-4">
                        <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                          <div>
                            <p className="font-medium text-ink-900">{item.label}</p>
                            <p className="text-sm text-slate-600">
                              {item.start_time} - {item.end_time}
                            </p>
                          </div>
                          {item.task_id ? (
                            <div className="flex flex-wrap gap-2">
                              <button disabled={busyAction !== null} onClick={() => progressTask("complete", item.task_id as string)} className="rounded-full border border-black/10 px-3 py-1.5 text-xs font-medium text-ink-900 disabled:opacity-50">
                                Complete
                              </button>
                              <button disabled={busyAction !== null} onClick={() => progressTask("skip", item.task_id as string)} className="rounded-full border border-black/10 px-3 py-1.5 text-xs font-medium text-ink-900 disabled:opacity-50">
                                Skip
                              </button>
                              <button disabled={busyAction !== null} onClick={() => progressTask("delay", item.task_id as string)} className="rounded-full border border-black/10 px-3 py-1.5 text-xs font-medium text-ink-900 disabled:opacity-50">
                                Delay 1 day
                              </button>
                              <button disabled={busyAction !== null} onClick={() => progressTask("move", item.task_id as string)} className="rounded-full border border-black/10 px-3 py-1.5 text-xs font-medium text-ink-900 disabled:opacity-50">
                                Move tomorrow
                              </button>
                            </div>
                          ) : null}
                        </div>
                      </div>
                    ))}
                  </div>
                ) : null}
              </div>
              <TaskList tasks={tasks} />
            </div>
            <div className="space-y-4">
              <TaskCreateForm onCreated={handleTaskCreated} />
              <div className="rounded-3xl border border-[var(--border)] bg-white/80 p-5">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Insight</p>
                {insight ? (
                  <div className="mt-3 space-y-3 text-sm text-slate-700">
                    <p className="font-medium text-ink-900">
                      {insight.completed_tasks}/{insight.total_tasks} tasks complete
                    </p>
                    <p>{insight.top_focus}</p>
                    <ul className="space-y-1">
                      {insight.highlights.map((item) => (
                        <li key={item}>- {item}</li>
                      ))}
                    </ul>
                  </div>
                ) : (
                  <p className="mt-2 text-sm text-slate-700">Insight will appear after today&apos;s data is available.</p>
                )}
              </div>
              <div className="rounded-3xl border border-[var(--border)] bg-white/80 p-5">
                <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Next</p>
                <p className="mt-2 text-sm text-slate-700">
                  Progress actions update task state, AI adjustment turns user changes into suggestions, and insight summarizes the day.
                </p>
              </div>
            </div>
          </div>
        ) : null}
      </section>
    </main>
  );
}
