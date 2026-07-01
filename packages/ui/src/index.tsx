import type { ButtonHTMLAttributes, InputHTMLAttributes, TextareaHTMLAttributes } from "react";

export function Button({ className, ...props }: ButtonHTMLAttributes<HTMLButtonElement>) {
  return <button className={["rounded-full bg-ink-800 px-5 py-3 text-sm font-medium text-white", className].filter(Boolean).join(" ")} {...props} />;
}

export function Input({ className, ...props }: InputHTMLAttributes<HTMLInputElement>) {
  return <input className={["w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3", className].filter(Boolean).join(" ")} {...props} />;
}

export function Textarea({ className, ...props }: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return <textarea className={["min-h-24 w-full rounded-2xl border border-[var(--border)] bg-white px-4 py-3", className].filter(Boolean).join(" ")} {...props} />;
}
