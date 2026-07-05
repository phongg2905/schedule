import type { SelectHTMLAttributes, DetailedHTMLProps } from "react";

import { cn } from "@/lib/cn";

export type SelectProps = DetailedHTMLProps<
  SelectHTMLAttributes<HTMLSelectElement>,
  HTMLSelectElement
>;

export function Select({ className, ...props }: Readonly<SelectProps>) {
  return <select className={cn("select-base", className)} {...props} />;
}
