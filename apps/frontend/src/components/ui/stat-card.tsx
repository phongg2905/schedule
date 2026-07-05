import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type StatCardProps = {
  label: string;
  value: string;
  hint?: string;
  accent?: "coral" | "sky" | "mint" | "lavender";
  icon?: ReactNode;
  className?: string;
};

const accentStyles: Record<string, string> = {
  coral: "bg-coral-50 text-coral-500",
  sky: "bg-sky-50 text-sky-400",
  mint: "bg-mint-50 text-mint-400",
  lavender: "bg-lavender-50 text-lavender-400",
};

const glowStyles: Record<string, string> = {
  coral: "shadow-[0_0_24px_rgba(255,122,92,0.08)]",
  sky: "shadow-[0_0_24px_rgba(107,162,255,0.08)]",
  mint: "shadow-[0_0_24px_rgba(79,208,137,0.08)]",
  lavender: "shadow-[0_0_24px_rgba(157,130,255,0.08)]",
};

const dotStyles: Record<string, string> = {
  coral: "bg-coral-500",
  sky: "bg-sky-400",
  mint: "bg-mint-400",
  lavender: "bg-lavender-400",
};

export function StatCard({
  label,
  value,
  hint,
  accent = "coral",
  icon,
  className,
}: Readonly<StatCardProps>) {
  return (
    <div
      className={cn(
        "ambient-card group relative overflow-hidden p-5 transition-all duration-300 hover:-translate-y-0.5",
        glowStyles[accent],
        className
      )}
    >
      {/* Accent dot */}
      <div
        className={cn(
          "absolute right-4 top-4 h-2 w-2 rounded-full opacity-40 transition-opacity group-hover:opacity-70",
          dotStyles[accent]
        )}
      />

      <div className="flex items-start justify-between gap-4">
        <div className="space-y-2">
          <p className="section-label">{label}</p>
          <p className="font-display text-2xl font-semibold tracking-tight text-neutral-900">
            {value}
          </p>
          {hint ? (
            <p className="text-sm leading-5 text-neutral-500">{hint}</p>
          ) : null}
        </div>
        {icon ? (
          <div
            className={cn(
              "flex h-11 w-11 shrink-0 items-center justify-center rounded-2xl transition-transform duration-300 group-hover:scale-105",
              accentStyles[accent]
            )}
          >
            {icon}
          </div>
        ) : null}
      </div>
    </div>
  );
}
