"use client";

import type { ReactNode } from "react";
import { useCallback, useRef, useState } from "react";
import { motion, useAnimation } from "@/lib/motion";
import { cn } from "@/lib/cn";

// ── Types ──

type PullToRefreshProps = {
  children: ReactNode;
  className?: string;
  /** Called when pull-to-refresh is triggered */
  onRefresh: () => Promise<void> | void;
  /** Disable pull-to-refresh */
  disabled?: boolean;
  /** Pull threshold in px (default: 60) */
  threshold?: number;
  /** Maximum pull distance in px (default: 100) */
  maxPull?: number;
};

// ── Pull Indicator ──

function RefreshIndicator({ progress, isRefreshing }: { progress: number; isRefreshing: boolean }) {
  const rotation = progress * 360;

  return (
    <motion.div
      className="flex items-center justify-center"
      initial={{ height: 0, opacity: 0 }}
      animate={{
        height: isRefreshing || progress > 0 ? 48 : 0,
        opacity: isRefreshing || progress > 0 ? 1 : 0,
      }}
      transition={{ duration: 0.25, ease: [0.25, 0.1, 0.25, 1] }}
    >
      <div className="flex items-center gap-2.5 rounded-pill bg-white/90 px-4 py-2 shadow-sm backdrop-blur-sm border border-border-light">
        {isRefreshing ? (
          <>
            <motion.svg
              viewBox="0 0 24 24"
              className="h-4 w-4 fill-none stroke-current stroke-[2] text-coral-500"
              animate={{ rotate: 360 }}
              transition={{ duration: 1, repeat: Infinity, ease: "linear" }}
            >
              <path d="M12 2v4M12 18v4M4.93 4.93l2.83 2.83M16.24 16.24l2.83 2.83M2 12h4M18 12h4" />
            </motion.svg>
            <span className="text-xs font-medium text-neutral-600">Refreshing...</span>
          </>
        ) : (
          <>
            <motion.svg
              viewBox="0 0 24 24"
              className="h-4 w-4 fill-none stroke-current stroke-[2] text-neutral-500"
              animate={{ rotate: rotation }}
              transition={{ duration: 0.1 }}
            >
              <path d="M1 4v6h6M23 20v-6h-6" />
              <path d="M20.49 9A9 9 0 005.64 5.64L1 10m22 4l-4.64 4.36A9 9 0 013.51 15" />
            </motion.svg>
            <span className="text-xs font-medium text-neutral-400">
              {progress >= 1 ? "Release to refresh" : "Pull to refresh"}
            </span>
          </>
        )}
      </div>
    </motion.div>
  );
}

// ── Component ──

export function PullToRefresh({
  children,
  className,
  onRefresh,
  disabled = false,
  threshold = 60,
  maxPull = 100,
}: Readonly<PullToRefreshProps>) {
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pullProgress, setPullProgress] = useState(0);
  const containerRef = useRef<HTMLDivElement>(null);
  const controls = useAnimation();
  const isCurrentlyRefreshing = useRef(false);

  const handleRefresh = useCallback(async () => {
    if (isCurrentlyRefreshing.current) return;
    isCurrentlyRefreshing.current = true;
    setIsRefreshing(true);

    try {
      await onRefresh();
    } finally {
      isCurrentlyRefreshing.current = false;
      setIsRefreshing(false);
      controls.start({ y: 0, transition: { type: "spring", stiffness: 300, damping: 25 } });
    }
  }, [onRefresh, controls]);

  return (
    <div ref={containerRef} className={cn("relative overflow-hidden", className)}>
      {/* Pull indicator area */}
      <div className="pointer-events-none absolute left-0 right-0 z-10 flex justify-center">
        <RefreshIndicator progress={pullProgress} isRefreshing={isRefreshing} />
      </div>

      {/* Draggable content */}
      <motion.div
        drag={disabled || isRefreshing ? false : "y"}
        dragConstraints={{ top: 0, bottom: maxPull }}
        dragElastic={0.3}
        dragMomentum={false}
        onDrag={(_, info) => {
          const progress = Math.min(info.offset.y / threshold, 1);
          setPullProgress(progress);
        }}
        onDragEnd={async (_, info) => {
          if (info.offset.y >= threshold) {
            controls.start({ y: threshold / 2, transition: { type: "spring", stiffness: 200, damping: 20 } });
            await handleRefresh();
          } else {
            controls.start({ y: 0, transition: { type: "spring", stiffness: 300, damping: 25 } });
          }
          setPullProgress(0);
        }}
        animate={controls}
        style={{ y: 0 }}
        className="relative z-20"
      >
        {children}
      </motion.div>
    </div>
  );
}
