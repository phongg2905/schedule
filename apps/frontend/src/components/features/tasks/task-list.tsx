"use client";

import { useTranslations } from "next-intl";

import { EmptyState } from "@/components/ui/empty-state";
import { Card } from "@/components/ui/card";
import { SectionHeader } from "@/components/ui/section-header";
import { useAppIntl } from "@/providers/intl-provider";

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

type Props = {
  tasks: Task[];
};

const statusAccent: Record<string, "coral" | "blue" | "success" | "warning"> = {
  todo: "blue",
  completed: "success",
  skipped: "warning",
  deferred: "warning",
  planned: "coral",
  draft: "blue",
  generated: "coral",
};

export function TaskList({ tasks }: Readonly<Props>) {
  const tTasks = useTranslations("tasks");
  const tCommon = useTranslations("common");
  const { formatDate, formatDateTime } = useAppIntl();

  return (
    <Card className="p-6 sm:p-8">
      <div className="space-y-5">
        <SectionHeader
          eyebrow={tTasks("list.eyebrow")}
          title="Task list"
          description="Review the tasks that feed the planning flow."
        />
        {tasks.length === 0 ? (
          <EmptyState
            illustration="tasks"
            title={tTasks("list.empty")}
            description="Once tasks exist, they appear here as polished cards."
          />
        ) : (
          <div className="grid gap-4">
            {tasks.map((task) => (
              <article key={task.id} className="rounded-[24px] border border-[var(--border)] bg-[linear-gradient(180deg,#ffffff_0%,#fbfdff_100%)] p-5 shadow-[0_10px_28px_rgba(15,23,42,0.05)]">
                <div className="flex flex-col gap-4">
                  <div className="flex flex-wrap items-start justify-between gap-3">
                    <div className="space-y-2">
                      <div className="flex items-center gap-2">
                        <h3 className="text-lg font-semibold tracking-tight text-[var(--foreground)]">{task.title}</h3>
                        {task.task_type === "flexible" && (
                          <span className="rounded-pill bg-lavender-50 px-2.5 py-0.5 text-[11px] font-medium text-lavender-500 border border-lavender-100">
                            {tTasks("taskType.flexible")}
                          </span>
                        )}
                      </div>
                      <p className="text-sm leading-6 text-[var(--text-secondary)]">{task.description ?? tCommon("noDescription")}</p>
                    </div>
                    <div className="flex flex-wrap items-center gap-2">
                      <span
                        className="ui-pill"
                        style={{
                          backgroundColor: "rgba(255,255,255,0.96)",
                          color: "var(--foreground)",
                          boxShadow:
                            task.status in statusAccent
                              ? task.status === "completed"
                                ? "0 0 0 1px rgba(109,213,140,0.18) inset"
                                : task.status === "planned" || task.status === "generated"
                                  ? "0 0 0 1px rgba(124,157,255,0.18) inset"
                                  : "0 0 0 1px rgba(255,122,122,0.18) inset"
                              : undefined,
                        }}
                      >
                        <span
                          className="mr-2 inline-flex h-2.5 w-2.5 rounded-full"
                          style={{
                            backgroundColor:
                              statusAccent[task.status] === "success"
                                ? "var(--success)"
                                : statusAccent[task.status] === "blue"
                                  ? "var(--accent-blue)"
                                  : statusAccent[task.status] === "warning"
                                    ? "var(--warning)"
                                    : "var(--accent)",
                          }}
                        />
                        {tTasks(`status.${task.status}`)}
                      </span>
                      {task.priority ? <span className="ui-pill">{tTasks(`priority.${task.priority}`)}</span> : null}
                    </div>
                  </div>
                  <div className="grid gap-3 text-sm text-[var(--text-secondary)] sm:grid-cols-2 lg:grid-cols-5">
                    <p>
                      <span className="font-medium text-[var(--foreground)]">{tTasks("list.startTime")}:</span>{" "}
                      {task.start_time || tCommon("none")}
                    </p>
                    <p>
                      <span className="font-medium text-[var(--foreground)]">{tTasks("list.deadline")}:</span>{" "}
                      {task.deadline ? formatDate(task.deadline) : tCommon("none")}
                    </p>
                    <p>
                      <span className="font-medium text-[var(--foreground)]">{tTasks("list.estimate")}:</span>{" "}
                      {task.estimated_duration ? `${task.estimated_duration} min` : tCommon("none")}
                    </p>
                    <p>
                      <span className="font-medium text-[var(--foreground)]">{tTasks("list.tags")}:</span>{" "}
                      {task.tags.length > 0 ? task.tags.join(", ") : tCommon("none")}
                    </p>
                    <p>
                      <span className="font-medium text-[var(--foreground)]">{tTasks("list.completed")}:</span>{" "}
                      {task.completed_at ? formatDateTime(task.completed_at) : tCommon("notYet")}
                    </p>
                  </div>
                </div>
              </article>
            ))}
          </div>
        )}
      </div>
    </Card>
  );
}
