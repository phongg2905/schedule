import Image from "next/image";
import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type IllustrationVariant = "hero" | "plan" | "tasks" | "insight" | "settings" | "chart" | "document";

type IllustrationProps = {
  variant?: IllustrationVariant;
  className?: string;
};

function Shell({ children, className }: Readonly<{ children: ReactNode; className?: string }>) {
  return (
    <div
      className={cn(
        "relative overflow-hidden rounded-[28px] border border-[var(--border)] bg-[linear-gradient(180deg,#ffffff_0%,#f8fafc_100%)] p-4 shadow-[0_18px_50px_rgba(15,23,42,0.08)]",
        className
      )}
    >
      <div className="absolute inset-0 bg-[radial-gradient(circle_at_20%_20%,rgba(124,157,255,0.14),transparent_34%),radial-gradient(circle_at_80%_14%,rgba(255,122,122,0.16),transparent_30%),radial-gradient(circle_at_50%_100%,rgba(109,213,140,0.10),transparent_35%)]" />
      <svg viewBox="0 0 320 220" className="relative h-auto w-full" role="img" aria-hidden="true">
        {children}
      </svg>
    </div>
  );
}

function BasePlatform() {
  return (
    <g>
      <rect x="52" y="160" width="216" height="22" rx="11" fill="#EEF2F8" />
      <rect x="72" y="142" width="176" height="24" rx="12" fill="#FFFFFF" stroke="#E8EDF5" />
    </g>
  );
}

function FloatGlow() {
  return (
    <g opacity="0.9">
      <circle cx="161" cy="86" r="62" fill="rgba(124,157,255,0.12)" />
      <circle cx="161" cy="86" r="44" fill="rgba(255,122,122,0.10)" />
    </g>
  );
}

function HeroIllustration() {
  return (
    <div className="overflow-hidden rounded-[34px] border border-[rgba(232,237,245,0.8)] bg-[linear-gradient(180deg,#ffffff_0%,#fafcff_100%)] shadow-[0_26px_90px_rgba(15,23,42,0.08)]">
      <div className="relative aspect-[7/6] w-full">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_18%_18%,rgba(255,122,122,0.08),transparent_28%),radial-gradient(circle_at_82%_20%,rgba(124,157,255,0.08),transparent_26%),radial-gradient(circle_at_50%_100%,rgba(109,213,140,0.06),transparent_34%)]" />
        <Image
          alt=""
          aria-hidden="true"
          className="object-cover"
          fill
          priority
          sizes="(max-width: 1024px) 100vw, 640px"
          src="/illustrations/hourglass-hero.png"
        />
      </div>
    </div>
  );
}

function PlanIllustration() {
  return (
    <Shell>
      <FloatGlow />
      <BasePlatform />
      <g transform="translate(86 48)">
        <rect x="0" y="0" width="58" height="78" rx="18" fill="#FFFFFF" stroke="#E8EDF5" />
        <rect x="72" y="14" width="72" height="54" rx="16" fill="#F8FAFC" stroke="#E8EDF5" />
        <rect x="90" y="28" width="36" height="10" rx="5" fill="#FF7A7A" opacity="0.88" />
        <rect x="90" y="44" width="50" height="8" rx="4" fill="#7C9DFF" opacity="0.52" />
        <rect x="16" y="14" width="26" height="12" rx="6" fill="#FF7A7A" opacity="0.18" />
        <rect x="16" y="34" width="30" height="8" rx="4" fill="#CBD5E1" />
        <rect x="16" y="48" width="20" height="8" rx="4" fill="#CBD5E1" />
      </g>
      <g transform="translate(206 58)">
        <path d="M0 18 18 0 36 18 18 36 0 18Z" fill="#FFFFFF" stroke="#E8EDF5" />
        <circle cx="18" cy="18" r="5" fill="#FF7A7A" opacity="0.85" />
      </g>
    </Shell>
  );
}

function TasksIllustration() {
  return (
    <Shell>
      <FloatGlow />
      <BasePlatform />
      <g transform="translate(78 42)">
        <rect x="0" y="0" width="112" height="68" rx="18" fill="#FFFFFF" stroke="#E8EDF5" />
        <rect x="12" y="12" width="88" height="10" rx="5" fill="#7C9DFF" opacity="0.24" />
        <rect x="12" y="30" width="64" height="8" rx="4" fill="#CBD5E1" />
        <rect x="12" y="44" width="76" height="8" rx="4" fill="#CBD5E1" />
      </g>
      <g transform="translate(190 50)">
        <rect x="0" y="0" width="58" height="88" rx="18" fill="#FFFFFF" stroke="#E8EDF5" />
        <rect x="10" y="14" width="38" height="8" rx="4" fill="#FF7A7A" opacity="0.3" />
        <rect x="10" y="30" width="30" height="8" rx="4" fill="#CBD5E1" />
        <rect x="10" y="46" width="34" height="8" rx="4" fill="#CBD5E1" />
      </g>
      <g transform="translate(168 98)">
        <rect x="0" y="0" width="72" height="18" rx="9" fill="#FF7A7A" opacity="0.16" />
      </g>
    </Shell>
  );
}

function InsightIllustration() {
  return (
    <Shell>
      <FloatGlow />
      <BasePlatform />
      <g transform="translate(90 44)">
        <rect x="0" y="0" width="128" height="86" rx="22" fill="#FFFFFF" stroke="#E8EDF5" />
        <path d="M18 62 34 52 50 58 70 34 90 44 110 24" fill="none" stroke="#7C9DFF" strokeWidth="4" strokeLinecap="round" strokeLinejoin="round" />
        <circle cx="34" cy="52" r="5" fill="#FF7A7A" />
        <circle cx="50" cy="58" r="5" fill="#6DD58C" />
        <circle cx="70" cy="34" r="5" fill="#FFC857" />
      </g>
      <g transform="translate(216 60)">
        <circle cx="16" cy="16" r="16" fill="#FF7A7A" opacity="0.16" />
        <circle cx="16" cy="16" r="9" fill="#FF7A7A" opacity="0.82" />
      </g>
    </Shell>
  );
}

function SettingsIllustration() {
  return (
    <Shell>
      <FloatGlow />
      <BasePlatform />
      <g transform="translate(104 42)">
        <rect x="0" y="0" width="106" height="96" rx="22" fill="#FFFFFF" stroke="#E8EDF5" />
        <circle cx="53" cy="48" r="18" fill="#F8FAFC" stroke="#E8EDF5" />
        <path d="M53 30v6M53 60v6M35 48h6M65 48h6M41 36l4 4M61 56l4 4M41 60l4-4M61 40l4-4" stroke="#7C9DFF" strokeWidth="3" strokeLinecap="round" />
        <circle cx="53" cy="48" r="6" fill="#FF7A7A" opacity="0.85" />
      </g>
    </Shell>
  );
}

function ChartIllustration() {
  return (
    <Shell>
      <FloatGlow />
      <BasePlatform />
      <g transform="translate(84 44)">
        <rect x="0" y="0" width="160" height="84" rx="22" fill="#FFFFFF" stroke="#E8EDF5" />
        <rect x="18" y="52" width="18" height="18" rx="8" fill="#FF7A7A" opacity="0.28" />
        <rect x="46" y="38" width="18" height="32" rx="8" fill="#7C9DFF" opacity="0.28" />
        <rect x="74" y="24" width="18" height="46" rx="8" fill="#6DD58C" opacity="0.28" />
        <rect x="102" y="16" width="18" height="54" rx="8" fill="#FFC857" opacity="0.28" />
        <path d="M18 28C34 30 48 20 68 26C86 31 98 16 120 20" fill="none" stroke="#7C9DFF" strokeWidth="4" strokeLinecap="round" />
      </g>
    </Shell>
  );
}

function DocumentIllustration() {
  return (
    <Shell>
      <FloatGlow />
      <BasePlatform />
      <g transform="translate(102 36)">
        <rect x="0" y="0" width="116" height="104" rx="22" fill="#FFFFFF" stroke="#E8EDF5" />
        <path d="M84 0 116 32H84V0Z" fill="#F8FAFC" stroke="#E8EDF5" />
        <rect x="16" y="20" width="54" height="10" rx="5" fill="#FF7A7A" opacity="0.24" />
        <rect x="16" y="40" width="80" height="8" rx="4" fill="#CBD5E1" />
        <rect x="16" y="54" width="66" height="8" rx="4" fill="#CBD5E1" />
        <rect x="16" y="68" width="72" height="8" rx="4" fill="#CBD5E1" />
      </g>
    </Shell>
  );
}

export function ModuleIllustration({ variant = "hero", className }: Readonly<IllustrationProps>) {
  const variants = {
    hero: <HeroIllustration />,
    plan: <PlanIllustration />,
    tasks: <TasksIllustration />,
    insight: <InsightIllustration />,
    settings: <SettingsIllustration />,
    chart: <ChartIllustration />,
    document: <DocumentIllustration />,
  } as const;

  return <div className={cn("w-full", className)}>{variants[variant]}</div>;
}
