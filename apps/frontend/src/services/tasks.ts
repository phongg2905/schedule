import { apiFetch } from "@/services/api";

export type Task = {
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

export type TaskCreateInput = {
  title: string;
  description?: string | null;
  deadline?: string | null;
  start_time?: string | null;
  task_type?: string;
  priority?: string | null;
  estimated_duration?: number | null;
  tags?: string[];
};

export type TaskUpdateInput = Partial<TaskCreateInput> & {
  status?: string;
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

export function updateTask(taskId: string, input: TaskUpdateInput) {
  return apiFetch<Task>(`/tasks/${taskId}`, {
    method: "PATCH",
    body: JSON.stringify(input),
  });
}

export function deleteTask(taskId: string) {
  return apiFetch<void>(`/tasks/${taskId}`, {
    method: "DELETE",
  });
}
