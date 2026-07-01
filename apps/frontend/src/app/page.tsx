import Link from "next/link";

export default function HomePage() {
  return (
    <main className="mx-auto flex min-h-screen max-w-5xl items-center px-6 py-16">
      <section className="max-w-2xl space-y-6 rounded-[28px] border border-[var(--border)] bg-[var(--surface)] p-8 shadow-soft backdrop-blur">
        <p className="text-sm uppercase tracking-[0.24em] text-slate-500">AI Planner</p>
        <h1 className="text-4xl font-semibold tracking-tight text-ink-900 sm:text-6xl">
          A planning companion built around decisions, not checklists.
        </h1>
        <p className="max-w-xl text-base leading-7 text-slate-700">
          Start with login or register. The first vertical slice focuses on authentication and task persistence before AI enters the loop.
        </p>
        <div className="flex gap-3">
          <Link className="rounded-full bg-ink-800 px-5 py-3 text-sm font-medium text-white" href="/login">
            Login
          </Link>
          <Link className="rounded-full border border-[var(--border)] px-5 py-3 text-sm font-medium text-ink-900" href="/register">
            Register
          </Link>
        </div>
      </section>
    </main>
  );
}
