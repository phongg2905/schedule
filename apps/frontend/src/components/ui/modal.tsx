"use client";

import type { ReactNode } from "react";
import { useEffect, useRef } from "react";

import { cn } from "@/lib/cn";

type ModalProps = {
  open: boolean;
  onClose: () => void;
  title?: string;
  description?: string;
  children: ReactNode;
  className?: string;
};

export function Modal({
  open,
  onClose,
  title,
  description,
  children,
  className,
}: Readonly<ModalProps>) {
  const overlayRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const handleEsc = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };

    if (open) {
      document.addEventListener("keydown", handleEsc);
      document.body.style.overflow = "hidden";
    }

    return () => {
      document.removeEventListener("keydown", handleEsc);
      document.body.style.overflow = "";
    };
  }, [open, onClose]);

  if (!open) return null;

  return (
    <div
      ref={overlayRef}
      className="fixed inset-0 z-50 flex items-center justify-center p-4"
      onClick={(e) => {
        if (e.target === overlayRef.current) onClose();
      }}
    >
      {/* Backdrop */}
      <div className="absolute inset-0 bg-neutral-900/20 backdrop-blur-sm animate-fade-in" />

      {/* Modal */}
      <div
        className={cn(
          "relative w-full max-w-lg animate-scale-in rounded-[28px] border border-border-light bg-white p-6 shadow-lift-lg sm:p-8",
          className
        )}
        role="dialog"
        aria-modal="true"
        aria-label={title}
      >
        {/* Close button */}
        <button
          onClick={onClose}
          className="absolute right-4 top-4 flex h-8 w-8 items-center justify-center rounded-full text-neutral-400 transition-colors hover:bg-neutral-100 hover:text-neutral-600"
          aria-label="Close"
        >
          <svg
            viewBox="0 0 20 20"
            className="h-4 w-4 fill-current"
          >
            <path
              fillRule="evenodd"
              d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z"
              clipRule="evenodd"
            />
          </svg>
        </button>

        {title ? (
          <div className="mb-6 pr-8">
            <h2 className="font-display text-xl font-semibold tracking-tight text-neutral-900">
              {title}
            </h2>
            {description ? (
              <p className="mt-1 text-sm text-neutral-500">{description}</p>
            ) : null}
          </div>
        ) : null}

        {children}
      </div>
    </div>
  );
}
