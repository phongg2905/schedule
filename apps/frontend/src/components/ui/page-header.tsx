import dynamic from "next/dynamic";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

const ModuleIllustration = dynamic(
  () => import("@/components/ui/illustrations").then((mod) => mod.ModuleIllustration),
  { ssr: false }
);

type PageHeaderProps = {
  eyebrow: string;
  title: string;
  description: string;
  illustration?: "hero" | "plan" | "tasks" | "insight" | "settings" | "chart" | "document";
  actions?: ReactNode;
  className?: string;
};

export function PageHeader({
  eyebrow,
  title,
  description,
  illustration = "hero",
  actions,
  className,
}: Readonly<PageHeaderProps>) {
  return (
    <div
      className={cn(
        "grid gap-6 lg:grid-cols-[1.1fr_0.9fr] lg:items-center",
        className
      )}
    >
      <div className="space-y-4">
        <p className="section-label text-coral-500">{eyebrow}</p>
        <div className="space-y-3">
          <h1 className="page-title max-w-3xl">{title}</h1>
          <p className="max-w-2xl text-base leading-7 text-neutral-500">
            {description}
          </p>
        </div>
        {actions ? (
          <div className="flex flex-wrap gap-3 pt-2">{actions}</div>
        ) : null}
      </div>
      {illustration ? (
        <div className="flex justify-start lg:justify-end">
          <div className="w-full max-w-[28rem]">
            <ModuleIllustration variant={illustration} />
          </div>
        </div>
      ) : null}
    </div>
  );
}
