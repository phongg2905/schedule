"use client";

import type { ReactNode } from "react";
import { useCallback, useRef, useState } from "react";
import { motion, AnimatePresence, type Variants, type TargetAndTransition, type VariantLabels, type Transition } from "@/lib/motion";
import { cn } from "@/lib/cn";

// ── Types ──

type SwipeAction = {
  direction: "left" | "right";
  label: string;
  icon: ReactNode;
  color: string; // tailwind class for bg
  onSwipe: () => void | Promise<void>;
};

type SwipeableCardProps = {
  children: ReactNode;
  className?: string;
  /** Swipe left action (e.g. complete) */
  leftAction?: SwipeAction;
  /** Swipe right action (e.g. delay/skip) */
  rightAction?: SwipeAction;
  /** Show background action hints when idle */
  showActionHints?: boolean;
  /** Disable swipe interaction */
  disabled?: boolean;
  /** Called when any swipe completes */
  onSwiped?: (direction: "left" | "right") => void;
  /** Threshold in px before action triggers (default: 100) */
  threshold?: number;
  /** Entry animation variants */
  variants?: Variants;
  /** Entry animation initial state */
  initial?: TargetAndTransition | VariantLabels;
  /** Entry animation animate state */
  animate?: TargetAndTransition | VariantLabels;
  /** Entry animation transition */
  transition?: Transition;
  /** Custom delay for entry animation */
  delay?: number;
};

// ── Config ──

const SWIPE_THRESHOLD = 100;
const SWIPE_VELOCITY = 500;

// Default entry animation
const defaultVariants: Variants = {
  hidden: { opacity: 0, x: -15, scale: 0.97 },
  visible: { opacity: 1, x: 0, scale: 1 },
};

// ── Component ──

export function SwipeableCard({
  children,
  className,
  leftAction,
  rightAction,
  showActionHints = true,
  disabled = false,
  onSwiped,
  threshold = SWIPE_THRESHOLD,
  variants,
  initial: customInitial,
  animate: customAnimate,
  transition: customTransition,
  delay = 0,
}: Readonly<SwipeableCardProps>) {
  const [isDragging, setIsDragging] = useState(false);
  const constraintsRef = useRef<HTMLDivElement>(null);

  const handleDragEnd = useCallback(
    (_: unknown, info: { offset: { x: number }; velocity: { x: number } }) => {
      setIsDragging(false);
      if (disabled) return;

      const offsetX = info.offset.x;
      const velocityX = info.velocity.x;

      // Swipe left
      if (offsetX < -threshold || velocityX < -SWIPE_VELOCITY) {
        leftAction?.onSwipe();
        onSwiped?.("left");
        return;
      }

      // Swipe right
      if (offsetX > threshold || velocityX > SWIPE_VELOCITY) {
        rightAction?.onSwipe();
        onSwiped?.("right");
        return;
      }
    },
    [disabled, leftAction, rightAction, onSwiped, threshold]
  );

  // Calculate drag progress for visual feedback
  const [dragX, setDragX] = useState(0);

  return (
    <div ref={constraintsRef} className={cn("relative overflow-hidden", className)}>
      {/* Background actions */}
      <div className="pointer-events-none absolute inset-0 flex">
        {/* Right action hint (swipe left reveals) */}
        {showActionHints && leftAction && (
          <motion.div
            className={cn(
              "absolute right-0 top-0 flex h-full w-20 items-center justify-center rounded-r-[16px] sm:w-24",
              leftAction.color
            )}
            animate={{
              opacity: dragX < -threshold / 2 ? 1 : 0.6,
              scale: dragX < -threshold / 2 ? 1.05 : 1,
            }}
            transition={{ duration: 0.2 }}
          >
            <div className="flex flex-col items-center gap-1 text-white">
              <span className="h-5 w-5">{leftAction.icon}</span>
              <span className="text-[10px] font-semibold whitespace-nowrap">{leftAction.label}</span>
            </div>
          </motion.div>
        )}

        {/* Left action hint (swipe right reveals) */}
        {showActionHints && rightAction && (
          <motion.div
            className={cn(
              "absolute left-0 top-0 flex h-full w-20 items-center justify-center rounded-l-[16px] sm:w-24",
              rightAction.color
            )}
            animate={{
              opacity: dragX > threshold / 2 ? 1 : 0.6,
              scale: dragX > threshold / 2 ? 1.05 : 1,
            }}
            transition={{ duration: 0.2 }}
          >
            <div className="flex flex-col items-center gap-1 text-white">
              <span className="h-5 w-5">{rightAction.icon}</span>
              <span className="text-[10px] font-semibold whitespace-nowrap">{rightAction.label}</span>
            </div>
          </motion.div>
        )}
      </div>

      {/* Draggable card with entry animation */}
      <motion.div
        variants={variants ?? defaultVariants}
        initial={customInitial ?? "hidden"}
        animate={customAnimate ?? "visible"}
        transition={customTransition ?? { delay, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
        drag={disabled ? false : "x"}
        dragConstraints={constraintsRef}
        dragElastic={0.2}
        dragMomentum={false}
        onDragStart={() => setIsDragging(true)}
        onDrag={(_, info) => setDragX(info.offset.x)}
        onDragEnd={handleDragEnd}
        whileTap={disabled ? {} : { scale: 0.98 }}
        className={cn(
          "relative z-10 cursor-default",
          !disabled && "touch-pan-y"
        )}
      >
        {children}
      </motion.div>

      {/* Completion success flash */}
      <AnimatePresence>
        {isDragging && Math.abs(dragX) > threshold * 0.75 && (
          <motion.div
            className="pointer-events-none absolute inset-0 z-20 rounded-[16px] ring-2 ring-mint-400/40"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
          />
        )}
      </AnimatePresence>
    </div>
  );
}

// ── Preset action icons ──

export const swipeActions = {
  complete: {
    label: "Complete",
    icon: (
      <svg viewBox="0 0 24 24" className="h-full w-full fill-none stroke-current stroke-[2.5]">
        <path d="M20 6L9 17l-5-5" />
      </svg>
    ),
  },
  delay: {
    label: "Tomorrow",
    icon: (
      <svg viewBox="0 0 24 24" className="h-full w-full fill-none stroke-current stroke-[2]">
        <circle cx="12" cy="12" r="9" />
        <path d="M12 7v5l3 3" />
      </svg>
    ),
  },
  skip: {
    label: "Skip",
    icon: (
      <svg viewBox="0 0 24 24" className="h-full w-full fill-none stroke-current stroke-[2.5]">
        <path d="M18 6L6 18M6 6l12 12" />
      </svg>
    ),
  },
  move: {
    label: "Move",
    icon: (
      <svg viewBox="0 0 24 24" className="h-full w-full fill-none stroke-current stroke-[2]">
        <path d="M5 12h14M12 5l7 7-7 7" />
      </svg>
    ),
  },
} as const;
