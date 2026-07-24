"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { useParams, useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { motion, type Variants } from "@/lib/motion";

import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { LoadingState } from "@/components/ui/loading-state";
import { Modal } from "@/components/ui/modal";
import { Textarea } from "@/components/ui/textarea";
import { getErrorMessage } from "@/lib/api-error";
import { useAppIntl } from "@/providers/intl-provider";
import { apiFetch } from "@/services/api";
import { fetchMe } from "@/services/auth";
import { cn } from "@/lib/cn";
import { deleteTask as deleteTaskRequest, updateTask as updateTaskRequest } from "@/services/tasks";
import { FadeIn, FadeInUp, StaggerContainer, StaggerItem } from "@/lib/motion";

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
  created_at?: string;
};

type TaskEditForm = {
  title: string;
  description: string;
  deadline: string;
  start_time: string;
  task_type: string;
  priority: string;
  estimated_duration: string;
  tags: string;
};

const priorityConfig: Record<string, { color: string; label: string }> = {
  urgent: { color: "bg-coral-400", label: "tasks.priority.urgent" },
  high: { color: "bg-[#F0B84A]", label: "tasks.priority.high" },
  normal: { color: "bg-sky-400", label: "tasks.priority.normal" },
  low: { color: "bg-neutral-300", label: "tasks.priority.low" },
};

const statusConfig: Record<string, { variant: "coral" | "sky" | "mint" | "lavender" | "neutral" | "warning"; label: string }> = {
  todo: { variant: "neutral", label: "tasks.status.todo" },
  completed: { variant: "mint", label: "tasks.status.completed" },
  skipped: { variant: "warning", label: "tasks.status.skipped" },
  deferred: { variant: "lavender", label: "tasks.status.deferred" },
  planned: { variant: "sky", label: "tasks.status.planned" },
  draft: { variant: "neutral", label: "tasks.status.draft" },
  generated: { variant: "coral", label: "tasks.status.generated" },
};

// ── Variants ──

const headingVariants: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 200, damping: 25 } },
};

const cardVariants: Variants = {
  hidden: { opacity: 0, y: 16, scale: 0.98 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    scale: 1,
    transition: { delay: 0.3 + i * 0.1, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] },
  }),
};

export default function TaskDetailPage() {
  const params = useParams();
  const router = useRouter();
  const tTasks = useTranslations("tasks");
  const tCommon = useTranslations("common");
  const tErrors = useTranslations("errors");
  const { formatDate } = useAppIntl();

  const [task, setTask] = useState<Task | null>(null);
  const [loading, setLoading] = useState(true);
  const [completing, setCompleting] = useState(false);
  const [editOpen, setEditOpen] = useState(false);
  const [editSaving, setEditSaving] = useState(false);
  const [editError, setEditError] = useState<string | null>(null);
  const [editForm, setEditForm] = useState<TaskEditForm>({
    title: "",
    description: "",
    deadline: "",
    start_time: "",
    task_type: "scheduled",
    priority: "normal",
    estimated_duration: "",
    tags: "",
  });

  async function load() {
    try {
      await fetchMe();
      const data = await apiFetch<Task>(`/tasks/${params.id}`);
      setTask(data);
    } catch { router.push("/tasks"); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, [params.id]);

  useEffect(() => {
    if (!task) return;
    setEditForm({
      title: task.title,
      description: task.description ?? "",
      deadline: task.deadline ?? "",
      start_time: task.start_time ?? "",
      task_type: task.task_type,
      priority: task.priority ?? "normal",
      estimated_duration: task.estimated_duration ? String(task.estimated_duration) : "",
      tags: task.tags.join(", "),
    });
  }, [task]);

  async function markComplete() {
    if (!task) return;
    setCompleting(true);
    try {
      await apiFetch(`/progress/tasks/${task.id}/complete`, { method: "POST", body: JSON.stringify({ reason: "Completed from detail view" }) });
      const updated = await apiFetch<Task>(`/tasks/${params.id}`);
      setTask(updated);
    } finally { setCompleting(false); }
  }

  async function saveTask() {
    if (!task) return;
    setEditSaving(true);
    setEditError(null);
    try {
      const updated = await updateTaskRequest(task.id, {
        title: editForm.title.trim(),
        description: editForm.description.trim() || null,
        deadline: editForm.deadline || null,
        start_time: editForm.start_time || null,
        task_type: editForm.task_type,
        priority: editForm.priority || null,
        estimated_duration: editForm.estimated_duration ? Number(editForm.estimated_duration) : null,
        tags: editForm.tags
          .split(",")
          .map((tag) => tag.trim())
          .filter(Boolean),
      });
      setTask(updated);
      setEditOpen(false);
    } catch (error) {
      setEditError(getErrorMessage(error, tErrors));
    } finally {
      setEditSaving(false);
    }
  }

  async function deleteCurrentTask() {
    if (!task) return;
    if (!window.confirm("Delete this task?")) return;
    try {
      await deleteTaskRequest(task.id);
      router.push("/tasks");
    } catch (error) {
      setEditError(getErrorMessage(error, tErrors));
      setEditOpen(true);
    }
  }

  if (loading) {
    return (
      <main className="mx-auto w-full max-w-4xl px-4 py-5 sm:px-6 lg:px-8">
        <FadeIn className="space-y-5 sm:space-y-6">
          <LoadingState lines={1} variant="card" />
          <LoadingState lines={5} variant="card" />
        </FadeIn>
      </main>
    );
  }

  if (!task) {
    return (
      <main className="mx-auto w-full max-w-4xl px-4 py-5 sm:px-6 lg:px-8">
        <motion.p initial={{ opacity: 0 }} animate={{ opacity: 1 }}>Task not found</motion.p>
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
          <Link href="/tasks"><Button variant="secondary" size="sm">Back to tasks</Button></Link>
        </motion.div>
      </main>
    );
  }

  const priorityInfo = task.priority ? priorityConfig[task.priority] : null;
  const statusInfo = statusConfig[task.status];

  return (
    <main className="mx-auto w-full max-w-4xl px-4 py-5 sm:px-6 lg:px-8">
      <motion.div className="space-y-5 sm:space-y-6 lg:space-y-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
        {/* Back link */}
        <FadeInUp>
          <Link href="/tasks" className="inline-flex items-center gap-1.5 text-sm font-medium text-neutral-500 hover:text-neutral-700 transition-colors">
            <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
            {tTasks("detail.backToTasks")}
          </Link>
        </FadeInUp>

        {/* Title & actions */}
        <motion.div
          className="flex flex-col gap-4 sm:flex-row sm:items-start sm:justify-between"
          variants={headingVariants}
          initial="hidden"
          animate="visible"
        >
          <div className="space-y-3">
            <motion.div
              className="flex flex-wrap items-center gap-2"
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.15, duration: 0.3 }}
            >
              {priorityInfo && <span className={cn("h-2 w-2 rounded-full", priorityInfo.color)} />}
              {statusInfo && <Badge variant={statusInfo.variant} size="sm" dot>{tTasks(statusInfo.label.replace("tasks.", ""))}</Badge>}
            </motion.div>
            <h1 className={cn("font-display text-3xl font-bold tracking-tight text-neutral-900 sm:text-4xl", task.status === "completed" && "line-through opacity-60")}>
              {task.title}
            </h1>
          </div>
          <motion.div
            className="flex shrink-0 gap-2 w-full sm:w-auto"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ delay: 0.3, type: "spring", stiffness: 200 }}
          >
            <motion.div whileHover={{ y: -2 }} whileTap={{ scale: 0.95 }} className="w-full sm:w-auto">
              <Button onClick={() => setEditOpen(true)} variant="secondary" size="sm" className="w-full sm:w-auto">
                {tTasks("detail.edit")}
              </Button>
            </motion.div>
            <motion.div whileHover={{ y: -2 }} whileTap={{ scale: 0.95 }} className="w-full sm:w-auto">
              <Button onClick={() => void deleteCurrentTask()} variant="ghost" size="sm" className="w-full sm:w-auto">
                {tTasks("detail.delete")}
              </Button>
            </motion.div>
            <motion.div whileHover={{ y: -2 }} whileTap={{ scale: 0.95 }} className="w-full sm:w-auto">
              <Button onClick={markComplete} disabled={completing || task.status === "completed"} variant={task.status === "completed" ? "ghost" : "primary"} size="sm" className="w-full sm:w-auto">
                {task.status === "completed" ? "✓ Completed" : completing ? "..." : tTasks("detail.markComplete")}
              </Button>
            </motion.div>
          </motion.div>
        </motion.div>

        {/* Description */}
        {task.description ? (
          <motion.div
            initial={{ opacity: 0, y: 16, scale: 0.98 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            transition={{ delay: 0.2, duration: 0.4 }}
          >
            <Card variant="glass" className="p-6 sm:p-8">
              <p className="section-label mb-3">{tTasks("detail.description")}</p>
              <div className="prose prose-sm max-w-none text-neutral-700 leading-relaxed">
                {task.description}
              </div>
            </Card>
          </motion.div>
        ) : null}

        {/* Metadata grid */}
        <StaggerContainer className="grid gap-3 sm:gap-4 grid-cols-2 md:grid-cols-2 lg:grid-cols-4">
          <StaggerItem>
            <MetaCard delay={0.25} icon={<svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></svg>} label={tTasks("detail.type")} value={task.task_type === "flexible" ? tTasks("taskType.flexible") : tTasks("taskType.scheduled")} />
          </StaggerItem>
          <StaggerItem>
            <MetaCard delay={0.3} icon={<svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></svg>} label={tTasks("detail.duration")} value={task.estimated_duration ? `${Math.floor(task.estimated_duration / 60)}h ${task.estimated_duration % 60}m` : tCommon("none")} />
          </StaggerItem>
          <StaggerItem>
            <MetaCard delay={0.35} icon={<svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 3" /></svg>} label={tTasks("detail.startTime")} value={task.start_time || tCommon("none")} />
          </StaggerItem>
          <StaggerItem>
            <MetaCard delay={0.35} icon={<svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><rect x="3" y="4" width="18" height="18" rx="2" /><path d="M16 2v4M8 2v4M3 10h18" /></svg>} label={tTasks("detail.deadline")} value={task.deadline ? formatDate(task.deadline) : tCommon("none")} />
          </StaggerItem>
          <StaggerItem>
            <MetaCard delay={0.4} icon={<svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" /><circle cx="12" cy="7" r="4" /></svg>} label={tTasks("detail.created")} value={task.created_at ? formatDate(task.created_at) : tCommon("notYet")} />
          </StaggerItem>
          <StaggerItem>
            <MetaCard delay={0.45} icon={<svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><polyline points="20 6 9 17 4 12" /></svg>} label={tTasks("detail.completed")} value={task.completed_at ? formatDate(task.completed_at) : tCommon("notYet")} />
          </StaggerItem>
        </StaggerContainer>

        {/* Labels / Tags */}
        {task.tags && task.tags.length > 0 ? (
          <motion.div className="space-y-3" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5, duration: 0.4 }}>
            <p className="section-label">{tTasks("detail.labels")}</p>
            <div className="flex flex-wrap gap-2">
              {task.tags.map((tag, i) => (
                <motion.span
                  key={tag}
                  className="rounded-pill bg-coral-50 px-3 py-1.5 text-xs font-medium text-coral-600"
                  initial={{ opacity: 0, scale: 0.8 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.55 + i * 0.05, type: "spring", stiffness: 200 }}
                >
                  {tag}
                </motion.span>
              ))}
            </div>
          </motion.div>
        ) : null}

        <motion.div
          variants={cardVariants}
          custom={0}
          initial="hidden"
          animate="visible"
          whileHover={{ y: -2, transition: { duration: 0.2 } }}
        >
          <Card variant="glass" className="p-6 transition-all duration-200 hover:shadow-card-hover">
            <div className="flex items-start gap-4">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-2xl bg-lavender-50 text-lavender-400">
                <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8]"><circle cx="12" cy="12" r="9" /><path d="M12 16v-4M12 8h.01" /></svg>
              </div>
              <div className="space-y-2">
                <p className="section-label">{tTasks("detail.aiExplanation")}</p>
                <p className="text-sm leading-6 text-neutral-500">
                  {task.status === "completed"
                    ? "This task is complete. Check Today or History for the progress trail."
                    : "Open Today to place this task on the schedule, then use progress actions to update it."}
                </p>
              </div>
            </div>
          </Card>
        </motion.div>
      </motion.div>

      <Modal
        open={editOpen}
        onClose={() => setEditOpen(false)}
        title={tTasks("detail.edit")}
        description="Update the task details and schedule metadata."
        className="max-w-2xl"
      >
        <div className="space-y-4">
          {editError ? (
            <div className="rounded-soft border border-coral-100 bg-coral-50 px-4 py-3 text-sm text-coral-700">
              {editError}
            </div>
          ) : null}

          <div className="grid gap-4 sm:grid-cols-2">
            <label className="space-y-1.5 sm:col-span-2">
              <span className="text-xs font-medium text-neutral-600">{tTasks("create.taskTitle")}</span>
              <Input value={editForm.title} onChange={(event) => setEditForm((current) => ({ ...current, title: event.target.value }))} />
            </label>
            <label className="space-y-1.5 sm:col-span-2">
              <span className="text-xs font-medium text-neutral-600">{tTasks("create.description")}</span>
              <Textarea value={editForm.description} onChange={(event) => setEditForm((current) => ({ ...current, description: event.target.value }))} rows={4} />
            </label>
            <label className="space-y-1.5">
              <span className="text-xs font-medium text-neutral-600">{tTasks("create.deadline")}</span>
              <Input type="date" value={editForm.deadline} onChange={(event) => setEditForm((current) => ({ ...current, deadline: event.target.value }))} />
            </label>
            <label className="space-y-1.5">
              <span className="text-xs font-medium text-neutral-600">{tTasks("create.startTime")}</span>
              <Input type="time" value={editForm.start_time} onChange={(event) => setEditForm((current) => ({ ...current, start_time: event.target.value }))} />
            </label>
            <label className="space-y-1.5">
              <span className="text-xs font-medium text-neutral-600">{tTasks("create.taskType")}</span>
              <select
                value={editForm.task_type}
                onChange={(event) => setEditForm((current) => ({ ...current, task_type: event.target.value }))}
                className="select-base"
              >
                <option value="scheduled">{tTasks("create.taskTypeScheduled")}</option>
                <option value="flexible">{tTasks("create.taskTypeFlexible")}</option>
              </select>
            </label>
            <label className="space-y-1.5">
              <span className="text-xs font-medium text-neutral-600">{tTasks("create.priority")}</span>
              <select
                value={editForm.priority}
                onChange={(event) => setEditForm((current) => ({ ...current, priority: event.target.value }))}
                className="select-base"
              >
                <option value="low">{tTasks("priority.low")}</option>
                <option value="normal">{tTasks("priority.normal")}</option>
                <option value="high">{tTasks("priority.high")}</option>
                <option value="urgent">{tTasks("priority.urgent")}</option>
              </select>
            </label>
            <label className="space-y-1.5">
              <span className="text-xs font-medium text-neutral-600">{tTasks("create.duration")}</span>
              <Input
                type="number"
                min="1"
                value={editForm.estimated_duration}
                onChange={(event) => setEditForm((current) => ({ ...current, estimated_duration: event.target.value }))}
              />
            </label>
            <label className="space-y-1.5 sm:col-span-2">
              <span className="text-xs font-medium text-neutral-600">{tTasks("create.labels")}</span>
              <Input
                value={editForm.tags}
                onChange={(event) => setEditForm((current) => ({ ...current, tags: event.target.value }))}
                placeholder={tTasks("create.labelsPlaceholder")}
              />
            </label>
          </div>

          <div className="flex flex-wrap justify-end gap-2 border-t border-border-light pt-4">
            <Button variant="ghost" onClick={() => setEditOpen(false)} disabled={editSaving}>
              {tCommon("cancel")}
            </Button>
            <Button variant="secondary" onClick={() => void saveTask()} disabled={editSaving || !editForm.title.trim()}>
              {editSaving ? tCommon("saving") : tCommon("save")}
            </Button>
          </div>
        </div>
      </Modal>
    </main>
  );
}

type MetaCardProps = {
  icon: React.ReactNode;
  label: string;
  value: string;
  delay?: number;
};

function MetaCard({ icon, label, value, delay = 0 }: Readonly<MetaCardProps>) {
  return (
    <motion.div
      className="rounded-soft border border-border-light bg-white/60 p-4 transition-all duration-200 hover:border-neutral-300 hover:shadow-md hover:-translate-y-0.5"
      whileHover={{ y: -2, boxShadow: "0 4px 12px rgba(0,0,0,0.06)" }}
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.35 }}
    >
      <motion.div
        className="mb-2 flex h-8 w-8 items-center justify-center rounded-[10px] bg-neutral-50 text-neutral-400"
        initial={{ scale: 0.8 }}
        animate={{ scale: 1 }}
        transition={{ delay: delay + 0.1, type: "spring", stiffness: 200 }}
      >
        {icon}
      </motion.div>
      <p className="text-xs text-neutral-400 mb-0.5">{label}</p>
      <p className="text-sm font-semibold text-neutral-900">{value}</p>
    </motion.div>
  );
}
