"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useTranslations } from "next-intl";

import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { SectionHeader } from "@/components/ui/section-header";
import { Textarea } from "@/components/ui/textarea";
import { ModuleIllustration } from "@/components/ui/illustrations";
import { getErrorMessage } from "@/lib/api-error";
import { apiFetch } from "@/services/api";

type Props = {
  onCreated: () => Promise<void>;
};

export function TaskCreateForm({ onCreated }: Readonly<Props>) {
  const tTasks = useTranslations("tasks");
  const tErrors = useTranslations("errors");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [estimatedDuration, setEstimatedDuration] = useState("");
  const [deadline, setDeadline] = useState("");
  const [startTime, setStartTime] = useState("");
  const [taskType, setTaskType] = useState("scheduled");
  const [priority, setPriority] = useState("normal");
  const [tags, setTags] = useState("");
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<string | null>(null);

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setMessage(null);
    try {
      await apiFetch("/tasks", {
        method: "POST",
        body: JSON.stringify({
          title,
          description: description || null,
          estimated_duration: estimatedDuration ? Number(estimatedDuration) : null,
          deadline: deadline || null,
          start_time: startTime || null,
          task_type: taskType,
          priority: priority || null,
          tags: tags
            .split(",")
            .map((tag) => tag.trim())
            .filter(Boolean),
        }),
      });
      setTitle("");
      setDescription("");
      setEstimatedDuration("");
      setDeadline("");
      setStartTime("");
      setTaskType("scheduled");
      setPriority("normal");
      setTags("");
      setMessage(tTasks("create.success"));
      await onCreated();
    } catch (error) {
      setMessage(getErrorMessage(error, tErrors));
    } finally {
      setLoading(false);
    }
  }

  return (
    <Card className="overflow-hidden p-6 sm:p-8">
      <div className="space-y-5">
        <ModuleIllustration variant="document" />
        <SectionHeader
          eyebrow={tTasks("create.eyebrow")}
          title={tTasks("create.title")}
          description="Capture the work you want to place into today."
        />
        <form onSubmit={submit} className="space-y-4">
          <Input placeholder={tTasks("create.taskTitle")} value={title} onChange={(event) => setTitle(event.target.value)} />
          <Textarea placeholder={tTasks("create.placeholder.description")} value={description} onChange={(event) => setDescription(event.target.value)} />
          <div className="grid gap-3 sm:grid-cols-2">
            <Input placeholder={tTasks("create.duration")} type="number" min="1" value={estimatedDuration} onChange={(event) => setEstimatedDuration(event.target.value)} />
            <Input type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} />
          </div>
          <div className="space-y-3">
            <label className="text-xs font-medium text-neutral-600">{tTasks("create.taskType")}</label>
            <div className="flex gap-2">
              <button type="button" onClick={() => setTaskType("scheduled")} className={`flex-1 rounded-pill border px-3 py-2 text-xs font-medium transition-all ${taskType === "scheduled" ? "border-coral-200 bg-coral-50 text-coral-600" : "border-border-light bg-white text-neutral-500"}`}>{tTasks("create.taskTypeScheduled")}</button>
              <button type="button" onClick={() => setTaskType("flexible")} className={`flex-1 rounded-pill border px-3 py-2 text-xs font-medium transition-all ${taskType === "flexible" ? "border-lavender-200 bg-lavender-50 text-lavender-600" : "border-border-light bg-white text-neutral-500"}`}>{tTasks("create.taskTypeFlexible")}</button>
            </div>
          </div>
          <div className="space-y-2">
            <label className="text-xs font-medium text-neutral-600">{tTasks("create.startTime")}</label>
            <Input type="time" value={startTime} onChange={(event) => setStartTime(event.target.value)} />
          </div>
          <div className="grid gap-3 sm:grid-cols-2">
            <Select value={priority} onChange={(event) => setPriority(event.target.value)}>
              <option value="low">{tTasks("priority.low")}</option>
              <option value="normal">{tTasks("priority.normal")}</option>
              <option value="high">{tTasks("priority.high")}</option>
              <option value="urgent">{tTasks("priority.urgent")}</option>
            </Select>
            <Input placeholder={tTasks("create.tags")} value={tags} onChange={(event) => setTags(event.target.value)} />
          </div>
          {message ? <p className="text-sm text-[var(--text-secondary)]">{message}</p> : null}
          <Button disabled={loading || !title.trim()} type="submit">
            {loading ? tTasks("create.submitting") : tTasks("create.submit")}
          </Button>
        </form>
      </div>
    </Card>
  );
}
