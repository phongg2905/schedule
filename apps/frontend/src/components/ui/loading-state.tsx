import { cn } from "@/lib/cn";

type LoadingStateProps = {
  lines?: number;
  className?: string;
  variant?: "card" | "inline";
};

export function LoadingState({
  lines = 3,
  className,
  variant = "card",
}: Readonly<LoadingStateProps>) {
  if (variant === "inline") {
    return (
      <div className={cn("space-y-3", className)}>
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={`loading-${index}`}
            className={cn(
              "relative h-4 animate-skeleton-pulse rounded-full bg-neutral-100",
              index === 0 ? "w-1/2" : index === 1 ? "w-4/5" : "w-3/5"
            )}
          >
            {/* Shimmer overlay */}
            <div className="absolute inset-0 overflow-hidden rounded-full">
              <div className="h-full w-full animate-shimmer bg-gradient-to-r from-transparent via-white/40 to-transparent" />
            </div>
          </div>
        ))}
      </div>
    );
  }

  return (
    <div
      className={cn(
        "ambient-card relative overflow-hidden p-6",
        className
      )}
    >
      {/* Shimmer overlay */}
      <div className="absolute inset-0 -translate-x-full animate-shimmer bg-gradient-to-r from-transparent via-white/30 to-transparent" />

      <div className="space-y-4">
        <div className="flex items-center gap-4">
          <div className="h-12 w-12 animate-skeleton-pulse rounded-2xl bg-neutral-100" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-1/3 animate-skeleton-pulse rounded-full bg-neutral-100" />
            <div className="h-3 w-1/2 animate-skeleton-pulse rounded-full bg-neutral-50" />
          </div>
        </div>
        {Array.from({ length: lines }).map((_, index) => (
          <div
            key={`loading-line-${index}`}
            className={cn(
              "h-3 animate-skeleton-pulse rounded-full bg-neutral-100",
              index === 0 ? "w-full" : index === 1 ? "w-5/6" : "w-2/3"
            )}
          />
        ))}
      </div>
    </div>
  );
}
