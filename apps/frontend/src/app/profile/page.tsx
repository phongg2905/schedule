"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { motion, type Variants } from "framer-motion";

import { Card } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Avatar } from "@/components/ui/avatar";
import { LoadingState } from "@/components/ui/loading-state";
import { apiFetch } from "@/services/api";
import { fetchMe, type User } from "@/services/auth";
import { FadeIn, FadeInUp, StaggerContainer } from "@/lib/motion";

type TaskCount = {
  total: number;
  completed: number;
};

// ── Variants ──

const avatarVariants: Variants = {
  hidden: { scale: 0.8, opacity: 0, rotate: -5 },
  visible: {
    scale: 1,
    opacity: 1,
    rotate: 0,
    transition: { type: "spring", stiffness: 220, damping: 20 },
  },
};

const iconVariants: Variants = {
  hidden: { scale: 0.8, rotate: -15 },
  visible: {
    scale: 1,
    rotate: 0,
    transition: { type: "spring", stiffness: 200, damping: 18 },
  },
};

const fieldVariants: Variants = {
  hidden: { opacity: 0, y: 12 },
  visible: (i: number) => ({
    opacity: 1,
    y: 0,
    transition: { delay: 0.35 + i * 0.08, duration: 0.4, ease: [0.25, 0.1, 0.25, 1] },
  }),
};

const staggerItemVariants: Variants = {
  hidden: { opacity: 0, y: 16 },
  visible: { opacity: 1, y: 0, transition: { duration: 0.4, ease: [0.25, 0.1, 0.25, 1] } },
  hover: {
    y: -4,
    boxShadow: "0 8px 25px rgba(0,0,0,0.08)",
    transition: { duration: 0.25, ease: [0.25, 0.1, 0.25, 1] },
  },
};

export default function ProfilePage() {
  const router = useRouter();
  const tProfile = useTranslations("profile");
  const [user, setUser] = useState<User | null>(null);
  const [taskCount, setTaskCount] = useState<TaskCount>({ total: 0, completed: 0 });
  const [loading, setLoading] = useState(true);

  async function load() {
    try {
      const me = await fetchMe();
      setUser(me);
      const tasks = await apiFetch<Array<{ status: string }>>("/tasks");
      setTaskCount({
        total: tasks.length,
        completed: tasks.filter((t) => t.status === "completed").length,
      });
    } catch { router.push("/login"); }
    finally { setLoading(false); }
  }

  useEffect(() => { void load(); }, []);

  const accountFields = [
    { label: tProfile("name"), value: user?.name || "" },
    { label: tProfile("email"), value: user?.email || "" },
    { label: tProfile("timezone"), value: user?.timezone || "" },
    { label: tProfile("role"), value: user?.role || "" },
  ];

  if (loading) {
    return (
      <main className="mx-auto max-w-5xl px-4 py-8 sm:px-6 lg:px-8">
        <FadeIn className="space-y-6">
          <LoadingState lines={1} variant="card" />
          <LoadingState lines={3} variant="card" />
        </FadeIn>
      </main>
    );
  }

  return (
    <main className="mx-auto max-w-5xl px-4 py-6 sm:px-6 lg:px-8">
      <motion.div
        className="space-y-8"
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.4 }}
      >
        {/* ── Header ── */}
        <div className="space-y-4">
          <FadeInUp>
            <p className="section-label text-coral-500">{tProfile("eyebrow")}</p>
          </FadeInUp>

          <motion.div
            className="flex items-center gap-6"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1, duration: 0.4 }}
          >
            <motion.div
              variants={avatarVariants}
              initial="hidden"
              animate="visible"
              whileHover={{ scale: 1.05, transition: { duration: 0.2 } }}
              whileTap={{ scale: 0.95 }}
            >
              <Avatar size="lg" fallback={user?.name}>
                {user?.name?.charAt(0).toUpperCase() || "?"}
              </Avatar>
            </motion.div>

            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: 0.25, duration: 0.4 }}
            >
              <h1 className="font-display text-3xl font-bold tracking-tight text-neutral-900">
                {user?.name}
              </h1>
              <p className="mt-1 text-sm text-neutral-500">{user?.email}</p>
            </motion.div>
          </motion.div>
        </div>

        {/* ── Stats ── */}
        <StaggerContainer className="grid gap-4 sm:grid-cols-3">
          <motion.div variants={staggerItemVariants} initial="hidden" animate="visible" whileHover="hover" whileTap={{ scale: 0.98 }}>
            <Card variant="glass" className="cursor-default p-6 text-center transition-colors duration-200">
              <motion.p
                className="font-display text-4xl font-semibold text-coral-500"
                initial={{ opacity: 0, scale: 0.7 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.3, type: "spring", stiffness: 180 }}
              >
                {taskCount.total}
              </motion.p>
              <p className="mt-1 text-xs font-medium text-neutral-500">{tProfile("stats.tasksCreated")}</p>
            </Card>
          </motion.div>
          <motion.div variants={staggerItemVariants} initial="hidden" animate="visible" whileHover="hover" whileTap={{ scale: 0.98 }}>
            <Card variant="glass" className="cursor-default p-6 text-center transition-colors duration-200">
              <motion.p
                className="font-display text-4xl font-semibold text-mint-500"
                initial={{ opacity: 0, scale: 0.7 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.35, type: "spring", stiffness: 180 }}
              >
                {taskCount.completed}
              </motion.p>
              <p className="mt-1 text-xs font-medium text-neutral-500">{tProfile("stats.tasksCreated")}</p>
            </Card>
          </motion.div>
          <motion.div variants={staggerItemVariants} initial="hidden" animate="visible" whileHover="hover" whileTap={{ scale: 0.98 }}>
            <Card variant="glass" className="cursor-default p-6 text-center transition-colors duration-200">
              <motion.p
                className="font-display text-4xl font-semibold text-lavender-400"
                initial={{ opacity: 0, scale: 0.7 }}
                animate={{ opacity: 1, scale: 1 }}
                transition={{ delay: 0.4, type: "spring", stiffness: 180 }}
              >
                &mdash;
              </motion.p>
              <p className="mt-1 text-xs font-medium text-neutral-500">{tProfile("stats.streak")}</p>
            </Card>
          </motion.div>
        </StaggerContainer>

        {/* ── Account Info ── */}
        <motion.div
          initial={{ opacity: 0, y: 24 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.25, duration: 0.5, ease: [0.25, 0.1, 0.25, 1] }}
        >
          <motion.div
            className="overflow-hidden rounded-soft"
            initial={{ scale: 0.98 }}
            animate={{ scale: 1 }}
            transition={{ delay: 0.25, duration: 0.4 }}
          >
            <Card variant="glass" className="overflow-hidden transition-all duration-300">
              <motion.div
                className="p-6 sm:p-8"
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3, duration: 0.4 }}
              >
                {/* Section header */}
                <motion.div
                  className="mb-6"
                  initial={{ opacity: 0, x: -10 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: 0.3, duration: 0.4 }}
                >
                  <motion.div
                    className="flex h-10 w-10 items-center justify-center rounded-2xl bg-coral-50 text-coral-500"
                    variants={iconVariants}
                    initial="hidden"
                    animate="visible"
                  >
                    <svg viewBox="0 0 24 24" className="h-5 w-5 fill-none stroke-current stroke-[1.8]">
                      <path d="M20 21v-2a4 4 0 00-4-4H8a4 4 0 00-4 4v2" />
                      <circle cx="12" cy="7" r="4" />
                    </svg>
                  </motion.div>
                  <h2 className="mt-3 font-display text-lg font-semibold text-neutral-900">
                    {tProfile("title")}
                  </h2>
                </motion.div>

                {/* Fields */}
                <div className="grid gap-5 sm:grid-cols-2">
                  {accountFields.map((field, i) => (
                    <motion.div
                      key={field.label}
                      className="space-y-1.5"
                      custom={i}
                      variants={fieldVariants}
                      initial="hidden"
                      animate="visible"
                    >
                      <label className="text-xs font-medium text-neutral-600">{field.label}</label>
                      <Input value={field.value} readOnly className="transition-all duration-200 focus-within:ring-2 focus-within:ring-coral-200/50" />
                    </motion.div>
                  ))}
                </div>
              </motion.div>
            </Card>
          </motion.div>
        </motion.div>
      </motion.div>
    </main>
  );
}
