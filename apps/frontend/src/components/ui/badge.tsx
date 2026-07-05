import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type BadgeVariant = "coral" | "sky" | "mint" | "lavender" | "neutral" | "warning";

type BadgeProps = {
  children: ReactNode;
  variant?: BadgeVariant;
  size?: "sm" | "md";
  dot?: boolean;
  className?: string;
};

const variantStyles: Record<BadgeVariant, string> = {
  coral: "bg-coral-50 text-coral-600 border-coral-100",
  sky: "bg-sky-50 text-sky-500 border-sky-100",
  mint: "bg-mint-50 text-mint-600 border-mint-100",
  lavender: "bg-lavender-50 text-lavender-500 border-lavender-100",
  neutral: "bg-neutral-50 text-neutral-600 border-neutral-100",
  warning: "bg-[#FFF8F0] text-[#E8A03A] border-[#FFF0DC]",
};

const dotVariants: Record<BadgeVariant, string> = {
  coral: "bg-coral-500",
  sky: "bg-sky-400",
  mint: "bg-mint-400",
  lavender: "bg-lavender-400",
  neutral: "bg-neutral-400",
  warning: "bg-[#E8A03A]",
};

const sizeStyles: Record<string, string> = {
  sm: "px-2.5 py-1 text-[11px]",
  md: "px-3 py-1.5 text-[12px]",
};

export function Badge({
  children,
  variant = "neutral",
  size = "sm",
  dot = false,
  className,
}: Readonly<BadgeProps>) {
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1.5 rounded-full border font-medium tracking-wide",
        variantStyles[variant],
        sizeStyles[size],
        className
      )}
    >
      {dot ? (
        <span
          className={cn(
            "inline-block h-1.5 w-1.5 rounded-full",
            dotVariants[variant]
          )}
        />
      ) : null}
      {children}
    </span>
  );
}
