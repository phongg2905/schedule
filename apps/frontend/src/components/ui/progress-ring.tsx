import { cn } from "@/lib/cn";

type ProgressRingProps = {
  progress: number; // 0-100
  size?: number;
  strokeWidth?: number;
  className?: string;
  label?: string;
  sublabel?: string;
};

export function ProgressRing({
  progress,
  size = 120,
  strokeWidth = 8,
  className,
  label,
  sublabel,
}: Readonly<ProgressRingProps>) {
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (Math.min(progress, 100) / 100) * circumference;

  const getColor = (pct: number) => {
    if (pct >= 80) return "#4FD089";
    if (pct >= 50) return "#6BA2FF";
    if (pct >= 25) return "#FF7A5C";
    return "#F0B84A";
  };

  const color = getColor(progress);

  return (
    <div className={cn("relative inline-flex flex-col items-center", className)}>
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="transform -rotate-90"
      >
        {/* Background circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke="rgba(36,33,30,0.06)"
          strokeWidth={strokeWidth}
        />
        {/* Progress circle */}
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={color}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          className="transition-all duration-1000 ease-out"
        />
      </svg>
      <div className="absolute inset-0 flex flex-col items-center justify-center">
        <span className="font-display text-2xl font-semibold tracking-tight text-neutral-900">
          {Math.round(progress)}%
        </span>
        {label ? (
          <span className="mt-0.5 text-[11px] font-medium text-neutral-500">
            {label}
          </span>
        ) : null}
      </div>
      {sublabel ? (
        <span className="mt-2 text-xs text-neutral-500">{sublabel}</span>
      ) : null}
    </div>
  );
}
