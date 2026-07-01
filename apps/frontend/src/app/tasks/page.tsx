"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/services/api";
import { fetchMe } from "@/services/auth";
import { TaskCreateForm, TaskList } from "@/features/tasks";

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

export default function TasksPage() {
  const router = useRouter();
  const [tasks, setTasks] = useState<Task[]>([]);

  async function load() {
    try {
      await fetchMe();
      const data = await apiFetch<Task[]>("/tasks");
      setTasks(data);
    } catch {
      router.push("/login");
    }
  }

  useEffect(() => {
    void load();
  }, []);

  return (
    <main className="mx-auto min-h-screen max-w-6xl px-6 py-10">
      <section className="rounded-[28px] border border-[var(--border)] bg-[var(--surface)] p-8 shadow-soft backdrop-blur">
        <div className="grid gap-6 lg:grid-cols-[0.8fr_1.2fr]">
          <TaskCreateForm onCreated={load} />
          <TaskList tasks={tasks} />
        </div>
      </section>
    </main>
  );
}
