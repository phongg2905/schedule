"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import { useRouter } from "next/navigation";

import { apiFetch } from "@/services/api";

export default function RegisterPage() {
  const router = useRouter();
  const [email, setEmail] = useState("");
  const [name, setName] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setLoading(true);
    setError(null);
    try {
      await apiFetch("/auth/register", {
        method: "POST",
        body: JSON.stringify({ email, name, password, timezone: "Asia/Saigon" }),
      });
      router.push("/login");
    } catch (err) {
      setError(err instanceof Error ? err.message : "Register failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="mx-auto flex min-h-screen max-w-md items-center px-6 py-16">
      <form onSubmit={onSubmit} className="w-full space-y-4 rounded-[28px] border border-[var(--border)] bg-[var(--surface)] p-8 shadow-soft backdrop-blur">
        <div>
          <p className="text-sm uppercase tracking-[0.24em] text-slate-500">Register</p>
          <h1 className="mt-2 text-3xl font-semibold tracking-tight text-ink-900">Create account</h1>
        </div>
        <input className="w-full rounded-2xl border border-[var(--border)] bg-white/80 px-4 py-3" placeholder="Name" value={name} onChange={(event) => setName(event.target.value)} />
        <input className="w-full rounded-2xl border border-[var(--border)] bg-white/80 px-4 py-3" placeholder="Email" value={email} onChange={(event) => setEmail(event.target.value)} />
        <input className="w-full rounded-2xl border border-[var(--border)] bg-white/80 px-4 py-3" placeholder="Password" type="password" value={password} onChange={(event) => setPassword(event.target.value)} />
        {error ? <p className="text-sm text-red-600">{error}</p> : null}
        <button disabled={loading} className="w-full rounded-full bg-ink-800 px-5 py-3 text-sm font-medium text-white disabled:opacity-60">
          {loading ? "Creating..." : "Register"}
        </button>
      </form>
    </main>
  );
}
