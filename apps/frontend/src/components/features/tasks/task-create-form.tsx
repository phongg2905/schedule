"use client";

import type { FormEvent } from "react";
import { useState } from "react";

import { apiFetch } from "@/services/api";

type Props = {
  onCreated: () => Promise<void>;
};

export function TaskCreateForm({ onCreated }: Readonly<Props>) {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [estimatedDuration, setEstimatedDuration] = useState("");
  const [deadline, setDeadline] = useState("");
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
      setPriority("normal");
      setTags("");
      setMessage("Task saved.");
      await onCreated();
    } catch (error) {
      setMessage(error instanceof Error ? error.message : "Task creation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={submit} className="rounded-3xl border border-[var(--border)] bg-white/80 p-5">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Create task</p>
      <div className="mt-4 space-y-3">
        <input className="w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3" placeholder="Task title" value={title} onChange={(event) => setTitle(event.target.value)} />
        <textarea className="min-h-24 w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3" placeholder="Description" value={description} onChange={(event) => setDescription(event.target.value)} />
        <div className="grid gap-3 sm:grid-cols-2">
          <input className="w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3" placeholder="Estimated minutes" type="number" min="1" value={estimatedDuration} onChange={(event) => setEstimatedDuration(event.target.value)} />
          <input className="w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3" type="date" value={deadline} onChange={(event) => setDeadline(event.target.value)} />
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <select className="w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3" value={priority} onChange={(event) => setPriority(event.target.value)}>
            <option value="low">Low</option>
            <option value="normal">Normal</option>
            <option value="high">High</option>
            <option value="urgent">Urgent</option>
          </select>
          <input className="w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3" placeholder="Tags, comma separated" value={tags} onChange={(event) => setTags(event.target.value)} />
        </div>
      </div>
      {message ? <p className="mt-3 text-sm text-slate-600">{message}</p> : null}
      <button disabled={loading || !title.trim()} className="mt-4 rounded-full bg-ink-800 px-5 py-3 text-sm font-medium text-white disabled:opacity-50">
        {loading ? "Saving..." : "Save task"}
      </button>
    </form>
  );
}
