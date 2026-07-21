import dynamic from "next/dynamic";
import Link from "next/link";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";
import { Button } from "@/components/ui/button";

// Lazy-load illustrations — heavy SVG components only rendered when empty state is visible
const ModuleIllustration = dynamic(
  () => import("@/components/ui/illustrations").then((mod) => mod.ModuleIllustration),
  {
    ssr: false,
    loading: () => (
      <div className="flex aspect-[320/220] w-full max-w-sm items-center justify-center rounded-[28px] border border-border-light bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] p-4">
        <div className="h-12 w-12 rounded-full bg-neutral-100 animate-pulse" />
      </div>
    ),
  }
);

type EmptyStateProps = {
  title: string;
  description: string;
  actionLabel?: string;
  actionHref?: string;
  onActionClick?: () => void;
  illustration?: "hero" | "plan" | "tasks" | "insight" | "settings" | "chart" | "document";
  footer?: ReactNode;
  className?: string;
};

export function EmptyState({
  title,
  description,
  actionLabel,
  actionHref,
  onActionClick,
  illustration = "hero",
  footer,
  className,
}: Readonly<EmptyStateProps>) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[28px] border border-border-light bg-white p-8 shadow-card transition-shadow hover:shadow-card-hover sm:p-10",
        className
      )}
    >
      {/* Ambient glow */}
      <div className="pointer-events-none absolute -inset-20 bg-[radial-gradient(circle_at_30%_30%,rgba(255,122,92,0.04),transparent_60%)]" />

      <div className="relative grid gap-8 lg:grid-cols-[0.85fr_1.15fr] lg:items-center">
        <div className="w-full max-w-sm">
          <ModuleIllustration variant={illustration} />
        </div>
        <div className="space-y-4">
          <p className="section-label text-neutral-400">Empty</p>
          <div className="space-y-2">
            <h3 className="font-display text-2xl font-semibold tracking-tight text-neutral-900">
              {title}
            </h3>
            <p className="max-w-xl text-sm leading-6 text-neutral-500">
              {description}
            </p>
          </div>
          {actionLabel ? (
            <div className="pt-1">
              {actionHref ? (
                <Link href={actionHref as never}>
                  <Button variant="primary" size="md">
                    {actionLabel}
                  </Button>
                </Link>
              ) : (
                <Button onClick={onActionClick}>{actionLabel}</Button>
              )}
            </div>
          ) : null}
          {footer ? <div className="pt-2">{footer}</div> : null}
        </div>
      </div>
    </div>
  );
}
