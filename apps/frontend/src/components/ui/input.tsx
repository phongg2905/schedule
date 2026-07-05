import type { InputHTMLAttributes, DetailedHTMLProps } from "react";

import { cn } from "@/lib/cn";

export type InputProps = DetailedHTMLProps<
  InputHTMLAttributes<HTMLInputElement>,
  HTMLInputElement
>;

export function Input({ className, ...props }: Readonly<InputProps>) {
  return <input className={cn("input-base", className)} {...props} />;
}
