import { apiFetch } from "@/services/api";

export type Task = {
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

export type TaskCreateInput = {
  title: string;
  description?: string | null;
  deadline?: string | null;
  priority?: string | null;
  estimated_duration?: number | null;
  tags?: string[];
};

export function listTasks() {
  return apiFetch<Task[]>("/tasks");
}

export function createTask(input: TaskCreateInput) {
  return apiFetch<Task>("/tasks", {
    method: "POST",
    body: JSON.stringify(input),
  });
}
