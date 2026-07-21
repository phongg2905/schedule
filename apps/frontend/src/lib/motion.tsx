"use client";

import type { HTMLAttributes, ReactNode } from "react";
import { forwardRef } from "react";
import {
  motion,
  AnimatePresence,
  useAnimation,
  type Variants,
  type HTMLMotionProps,
  type TargetAndTransition,
  type VariantLabels,
  type Transition,
} from "framer-motion";

// ─── Reusable Variants ───

const easeOut = [0.25, 0.1, 0.25, 1] as const;

export const fadeIn: Variants = {
  hidden: { opacity: 0 },
  visible: { opacity: 1, transition: { duration: 0.5, ease: easeOut } },
};

export const fadeInUp: Variants = {
  hidden: { opacity: 0, y: 20 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: easeOut } },
};

export const fadeInDown: Variants = {
  hidden: { opacity: 0, y: -12 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: easeOut } },
};

export const fadeInLeft: Variants = {
  hidden: { opacity: 0, x: -20 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.5, ease: easeOut } },
};

export const fadeInRight: Variants = {
  hidden: { opacity: 0, x: 20 },
  visible: { opacity: 1, x: 0, transition: { duration: 0.5, ease: easeOut } },
};

export const scaleIn: Variants = {
  hidden: { opacity: 0, scale: 0.95 },
  visible: { opacity: 1, scale: 1, transition: { duration: 0.35, ease: easeOut } },
};

export const slideUp: Variants = {
  hidden: { opacity: 0, y: 40 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.5, ease: easeOut } },
};

export const staggerContainer: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: {
      staggerChildren: 0.07,
      delayChildren: 0.1,
      ease: easeOut,
    },
  },
};

export const staggerItem: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: easeOut } },
};

// ─── Page Transition ───

export const pageTransition: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { duration: 0.4, ease: easeOut, when: "beforeChildren", staggerChildren: 0.06 },
  },
};

// ─── Mobile-Specific Variants ───

/** Spring-pop entrance for modals, sheets, badges */
export const springPop: Variants = {
  hidden: { opacity: 0, scale: 0.85 },
  visible: { opacity: 1, scale: 1, transition: { type: "spring", stiffness: 260, damping: 20 } },
  exit: { opacity: 0, scale: 0.85, transition: { duration: 0.15 } },
};

/** Slide-up sheet animation (bottom sheets, mobile menus) */
export const slideUpSheet: Variants = {
  hidden: { opacity: 0, y: "100%" },
  visible: { opacity: 1, y: 0, transition: { type: "spring", stiffness: 300, damping: 30, mass: 1 } },
  exit: { opacity: 0, y: "100%", transition: { duration: 0.2, ease: "easeIn" } },
};

/** Staggered list with smaller gap for mobile */
export const mobileStagger: Variants = {
  hidden: { opacity: 0 },
  visible: {
    opacity: 1,
    transition: { staggerChildren: 0.04, delayChildren: 0.05 },
  },
};

/** Bounce tap feedback for interactive elements */
export const tapBounce = {
  whileTap: { scale: 0.92, transition: { duration: 0.08 } },
};

/** Gentle press feedback for buttons and cards */
export const pressFeedback = {
  whileHover: { scale: 1.02, transition: { duration: 0.15, ease: "easeOut" } },
  whileTap: { scale: 0.96, transition: { duration: 0.08 } },
};

/** Shimmer skeleton loading animation */
export const shimmerVariants: Variants = {
  animate: {
    backgroundPosition: ["200% 0", "-200% 0"],
    transition: { duration: 1.5, repeat: Infinity, ease: "linear" },
  },
};

// ─── Hover / Tap ───

export const hoverLift = {
  whileHover: { y: -2, transition: { duration: 0.2, ease: "easeOut" } },
  whileTap: { y: 0, scale: 0.98, transition: { duration: 0.1 } },
};

export const hoverScale = {
  whileHover: { scale: 1.03, transition: { duration: 0.2, ease: "easeOut" } },
  whileTap: { scale: 0.97, transition: { duration: 0.1 } },
};

// ─── Re-exported framer-motion for centralized importing ───
// Import from this file instead of "framer-motion" directly to enable
// better tree-shaking and bundle optimization across pages.
export { motion, AnimatePresence, useAnimation };
export type { Variants, HTMLMotionProps, TargetAndTransition, VariantLabels, Transition };

// ─── Wrapper Components ───

type MotionDivProps = HTMLMotionProps<"div"> & {
  children: ReactNode;
};

export function MotionDiv({ children, ...props }: Readonly<MotionDivProps>) {
  return <motion.div {...props}>{children}</motion.div>;
}

export function FadeIn({
  children,
  className,
  delay = 0,
  ...props
}: Readonly<{ children: ReactNode; className?: string; delay?: number } & Omit<HTMLMotionProps<"div">, "children">>) {
  return (
    <motion.div
      className={className}
      variants={fadeIn}
      initial="hidden"
      animate="visible"
      transition={{ delay, duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

export function FadeInUp({
  children,
  className,
  delay = 0,
  ...props
}: Readonly<{ children: ReactNode; className?: string; delay?: number } & Omit<HTMLMotionProps<"div">, "children">>) {
  return (
    <motion.div
      className={className}
      variants={fadeInUp}
      initial="hidden"
      animate="visible"
      transition={{ delay, duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

export function FadeInDown({
  children,
  className,
  delay = 0,
  ...props
}: Readonly<{ children: ReactNode; className?: string; delay?: number } & Omit<HTMLMotionProps<"div">, "children">>) {
  return (
    <motion.div
      className={className}
      variants={fadeInDown}
      initial="hidden"
      animate="visible"
      transition={{ delay, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

export function StaggerContainer({
  children,
  className,
  ...props
}: Readonly<{ children: ReactNode; className?: string } & Omit<HTMLMotionProps<"div">, "children">>) {
  return (
    <motion.div className={className} variants={staggerContainer} initial="hidden" animate="visible" {...props}>
      {children}
    </motion.div>
  );
}

export function StaggerItem({
  children,
  className,
  ...props
}: Readonly<{ children: ReactNode; className?: string } & Omit<HTMLMotionProps<"div">, "children">>) {
  return (
    <motion.div className={className} variants={staggerItem} {...props}>
      {children}
    </motion.div>
  );
}

export function PageWrapper({
  children,
  className,
  ...props
}: Readonly<{ children: ReactNode; className?: string } & Omit<HTMLMotionProps<"div">, "children">>) {
  return (
    <motion.div className={className} variants={pageTransition} initial="hidden" animate="visible" {...props}>
      {children}
    </motion.div>
  );
}

// ─── Mobile Wrapper Components ───

/** Springs content in with a bounce (for alerts, confirmations, badges) */
export function SpringPop({
  children,
  className,
  ...props
}: Readonly<{ children: ReactNode; className?: string } & Omit<HTMLMotionProps<"div">, "children">>) {
  return (
    <motion.div className={className} variants={springPop} initial="hidden" animate="visible" exit="exit" {...props}>
      {children}
    </motion.div>
  );
}

/** Slide-up sheet from bottom (for mobile menus, bottom sheets) */
export function SlideUpSheet({
  children,
  className,
  ...props
}: Readonly<{ children: ReactNode; className?: string } & Omit<HTMLMotionProps<"div">, "children">>) {
  return (
    <motion.div className={className} variants={slideUpSheet} initial="hidden" animate="visible" exit="exit" {...props}>
      {children}
    </motion.div>
  );
}

/** Mobile staggered list with smaller gaps */
export function MobileStaggerContainer({
  children,
  className,
  ...props
}: Readonly<{ children: ReactNode; className?: string } & Omit<HTMLMotionProps<"div">, "children">>) {
  return (
    <motion.div className={className} variants={mobileStagger} initial="hidden" animate="visible" {...props}>
      {children}
    </motion.div>
  );
}

/** Pressable wrapper with spring feedback */
export function Pressable({
  children,
  className,
  onClick,
  ...props
}: Readonly<{ children: ReactNode; className?: string; onClick?: () => void } & Omit<HTMLMotionProps<"div">, "children">>) {
  return (
    <motion.div
      className={className}
      whileHover={{ scale: 1.02, transition: { duration: 0.15 } }}
      whileTap={{ scale: 0.96, transition: { duration: 0.08 } }}
      onClick={onClick}
      role="button"
      tabIndex={0}
      onKeyDown={(e) => { if (onClick && (e.key === "Enter" || e.key === " ")) { e.preventDefault(); onClick(); } }}
      {...props}
    >
      {children}
    </motion.div>
  );
}

// ─── Animated Card ───

type AnimatedCardProps = HTMLAttributes<HTMLDivElement> & {
  children: ReactNode;
  className?: string;
  delay?: number;
};

export const AnimatedCard = forwardRef<HTMLDivElement, AnimatedCardProps>(
  ({ children, className, delay = 0, ...props }, ref) => {
    return (
      <motion.div
        ref={ref}
        className={className}
        variants={staggerItem}
        initial="hidden"
        whileInView="visible"
        viewport={{ once: true, margin: "-30px" }}
        transition={{ delay, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] }}
        whileHover={{ y: -2, transition: { duration: 0.2 } }}
        {...(props as HTMLMotionProps<"div">)}
      >
        {children}
      </motion.div>
    );
  }
);
AnimatedCard.displayName = "AnimatedCard";
