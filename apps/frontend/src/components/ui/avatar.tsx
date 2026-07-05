import type { ReactNode } from "react";

import { cn } from "@/lib/cn";

type AvatarProps = {
  src?: string;
  alt?: string;
  fallback?: string;
  size?: "sm" | "md" | "lg";
  className?: string;
  children?: ReactNode;
};

const sizeStyles: Record<string, string> = {
  sm: "h-8 w-8 text-[11px]",
  md: "h-10 w-10 text-[13px]",
  lg: "h-12 w-12 text-[15px]",
};

const gradients = [
  "from-coral-400 to-coral-300",
  "from-sky-400 to-sky-300",
  "from-mint-400 to-mint-300",
  "from-lavender-400 to-lavender-300",
];

function hashString(str: string): number {
  let hash = 0;
  for (let i = 0; i < str.length; i++) {
    const char = str.charCodeAt(i);
    hash = (hash << 5) - hash + char;
    hash |= 0;
  }
  return Math.abs(hash);
}

export function Avatar({
  src,
  alt = "",
  fallback,
  size = "md",
  className,
  children,
}: Readonly<AvatarProps>) {
  const gradientIndex = fallback ? hashString(fallback) % gradients.length : 0;

  if (src) {
    return (
      <div
        className={cn(
          "relative inline-flex shrink-0 overflow-hidden rounded-full",
          sizeStyles[size],
          className
        )}
      >
        <img
          src={src}
          alt={alt}
          className="h-full w-full object-cover"
        />
      </div>
    );
  }

  return (
    <div
      className={cn(
        "relative inline-flex shrink-0 items-center justify-center rounded-full bg-gradient-to-br font-semibold text-white",
        gradients[gradientIndex],
        sizeStyles[size],
        className
      )}
      aria-label={alt || fallback}
    >
      {children ?? (fallback ? fallback.charAt(0).toUpperCase() : "?")}
    </div>
  );
}
