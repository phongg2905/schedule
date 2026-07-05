import type { TextareaHTMLAttributes, DetailedHTMLProps } from "react";

import { cn } from "@/lib/cn";

export type TextareaProps = DetailedHTMLProps<
  TextareaHTMLAttributes<HTMLTextAreaElement>,
  HTMLTextAreaElement
>;

export function Textarea({ className, ...props }: Readonly<TextareaProps>) {
  return (
    <textarea className={cn("textarea-base", className)} {...props} />
  );
}
