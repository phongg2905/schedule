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

type Props = {
  tasks: Task[];
};

export function TaskList({ tasks }: Readonly<Props>) {
  return (
    <div className="rounded-3xl border border-[var(--border)] bg-white/80 p-5">
      <p className="text-xs uppercase tracking-[0.2em] text-slate-500">Tasks</p>
      <div className="mt-4 space-y-3">
        {tasks.length === 0 ? (
          <p className="text-sm text-slate-600">No tasks yet. Create the first one to verify persistence.</p>
        ) : (
          tasks.map((task) => (
            <article key={task.id} className="rounded-2xl border border-black/5 bg-[rgba(247,247,242,0.7)] p-4">
              <h3 className="font-medium text-ink-900">{task.title}</h3>
              <p className="mt-1 text-sm text-slate-600">{task.description ?? "No description"}</p>
              <p className="mt-2 text-xs uppercase tracking-[0.18em] text-slate-500">
                {task.status} {task.priority ? `· ${task.priority}` : ""}
              </p>
              <div className="mt-3 space-y-1 text-sm text-slate-700">
                <p>Deadline: {task.deadline ?? "None"}</p>
                <p>Estimate: {task.estimated_duration ? `${task.estimated_duration} min` : "None"}</p>
                <p>Tags: {task.tags.length > 0 ? task.tags.join(", ") : "None"}</p>
                <p>Completed: {task.completed_at ?? "Not yet"}</p>
              </div>
            </article>
          ))
        )}
      </div>
    </div>
  );
}
