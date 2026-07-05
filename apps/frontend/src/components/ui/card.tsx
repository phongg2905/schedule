import type { HTMLAttributes } from "react";

import { cn } from "@/lib/cn";

type CardVariant = "glass" | "ambient" | "ghost";

type CardProps = HTMLAttributes<HTMLDivElement> & {
  variant?: CardVariant;
};

const variantStyles: Record<CardVariant, string> = {
  glass: "glass-card",
  ambient: "ambient-card",
  ghost: "bg-transparent",
};

export function Card({
  className,
  variant = "ambient",
  ...props
}: Readonly<CardProps>) {
  return (
    <div
      className={cn(variantStyles[variant], className)}
      {...props}
    />
  );
}

export function CardHeader({
  className,
  ...props
}: Readonly<HTMLAttributes<HTMLDivElement>>) {
  return (
    <div
      className={cn("flex items-start justify-between gap-4", className)}
      {...props}
    />
  );
}

export function CardBody({
  className,
  ...props
}: Readonly<HTMLAttributes<HTMLDivElement>>) {
  return (
    <div
      className={cn("space-y-4", className)}
      {...props}
    />
  );
}
