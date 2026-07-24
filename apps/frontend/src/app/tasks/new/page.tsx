"use client";

import type { FormEvent } from "react";
import { useState } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useTranslations } from "next-intl";
import { motion, AnimatePresence, type Variants } from "@/lib/motion";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Textarea } from "@/components/ui/textarea";
import { Card } from "@/components/ui/card";
import { getErrorMessage } from "@/lib/api-error";
import { cn } from "@/lib/cn";
import { formatDateKey } from "@/lib/date";
import { apiFetch } from "@/services/api";
import { fetchMe } from "@/services/auth";
import { TimePicker } from "@/components/ui/time-picker";
import { FadeInUp, StaggerContainer, StaggerItem } from "@/lib/motion";

type TaskFormData = {
  title: string;
  description: string;
  deadline: string;
  start_time: string;
  priority: string;
  estimated_duration: number | null;
  tags: string[];
};

const durationPresets = [
  { value: 15, labelKey: "durationPreset_15" },
  { value: 30, labelKey: "durationPreset_30" },
  { value: 60, labelKey: "durationPreset_60" },
  { value: 120, labelKey: "durationPreset_120" },
  { value: 240, labelKey: "durationPreset_240" },
  { value: 480, labelKey: "durationPreset_480" },
];

const priorityOptions = [
  { value: "low", labelKey: "priorityLow" },
  { value: "normal", labelKey: "priorityNormal" },
  { value: "high", labelKey: "priorityHigh" },
  { value: "urgent", labelKey: "priorityUrgent" },
];

const categories = [
  { value: "work", label: "Work", color: "bg-coral-50 text-coral-600 border-coral-100" },
  { value: "personal", label: "Personal", color: "bg-sky-50 text-sky-500 border-sky-100" },
  { value: "health", label: "Health", color: "bg-mint-50 text-mint-600 border-mint-100" },
  { value: "study", label: "Study", color: "bg-lavender-50 text-lavender-500 border-lavender-100" },
  { value: "finance", label: "Finance", color: "bg-[#FFF8F0] text-[#E8A03A] border-[#FFF0DC]" },
  { value: "shopping", label: "Shopping", color: "bg-neutral-50 text-neutral-600 border-neutral-100" },
  { value: "project", label: "Project", color: "bg-[#F0FCF5] text-[#34B870] border-[#DAF7E6]" },
];

// ── Variants ──

const successIconVariants: Variants = {
  hidden: { scale: 0, rotate: -180 },
  visible: { scale: 1, rotate: 0, transition: { type: "spring", stiffness: 260, damping: 20 } },
};

const successTextVariants: Variants = {
  hidden: { opacity: 0, y: 10 },
  visible: { opacity: 1, y: 0, transition: { delay: 0.2, duration: 0.4 } },
};

export default function CreateTaskPage() {
  const router = useRouter();
  const tTasks = useTranslations("tasks");
  const tCommon = useTranslations("common");
  const tErrors = useTranslations("errors");
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [selectedDuration, setSelectedDuration] = useState<number | null>(null);
  const [customDuration, setCustomDuration] = useState("");
  const [showCustomDuration, setShowCustomDuration] = useState(false);
  const [selectedDeadline, setSelectedDeadline] = useState<string>("");
  const [showCustomDate, setShowCustomDate] = useState(false);
  const [selectedStartTime, setSelectedStartTime] = useState("");
  const [selectedTaskType, setSelectedTaskType] = useState("scheduled");
  const [selectedPriority, setSelectedPriority] = useState("normal");
  const [selectedCategory, setSelectedCategory] = useState("");
  const [tagInput, setTagInput] = useState("");
  const [tags, setTags] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState(false);

  function getDateForOption(option: string): string {
    const today = new Date();
    switch (option) {
      case "today": return formatDateKey(today);
      case "tomorrow": return formatDateKey(new Date(today.getTime() + 86400000));
      case "weekend": {
        const daysUntilWeekend = (6 - today.getDay() + 7) % 7 || 7;
        return formatDateKey(new Date(today.getTime() + daysUntilWeekend * 86400000));
      }
      case "nextWeek": {
        const daysUntilNextWeek = (8 - today.getDay()) % 7 || 7;
        return formatDateKey(new Date(today.getTime() + daysUntilNextWeek * 86400000));
      }
      default: return "";
    }
  }

  async function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!title.trim()) return;
    setLoading(true);
    setError(null);

    try {
      await fetchMe();
      const duration = showCustomDuration && customDuration ? parseInt(customDuration, 10) : selectedDuration;
      const deadline = selectedDeadline || null;

      await apiFetch("/tasks", {
        method: "POST",
        body: JSON.stringify({
          title: title.trim(),
          description: description.trim() || null,
          deadline: deadline || null,
          start_time: selectedStartTime || null,
          task_type: selectedTaskType,
          priority: selectedPriority,
          estimated_duration: duration,
          tags: [...tags, ...(selectedCategory ? [selectedCategory] : [])],
        }),
      });

      setSuccess(true);
      setTimeout(() => router.push("/tasks"), 1500);
    } catch (err) {
      setError(getErrorMessage(err, tErrors));
    } finally {
      setLoading(false);
    }
  }

  function addTag(tag: string) {
    const trimmed = tag.trim().toLowerCase();
    if (trimmed && !tags.includes(trimmed)) {
      setTags([...tags, trimmed]);
    }
    setTagInput("");
  }

  function removeTag(tag: string) {
    setTags(tags.filter((t) => t !== tag));
  }

  const formSections = [
    { key: "title-section", content: (animate: boolean) => (
      <motion.div key="title" className="space-y-2" initial={animate ? { opacity: 0, y: 10 } : false} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.4 }}>
        <label className="text-xs font-medium text-neutral-600">{tTasks("create.taskTitle")}</label>
        <input
          type="text"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          placeholder={tTasks("create.titlePlaceholder")}
          required
          autoFocus
          className="w-full border-0 border-b-2 border-neutral-200 bg-transparent px-0 py-3 font-display text-2xl font-semibold tracking-tight text-neutral-900 outline-none transition-colors placeholder:text-neutral-300 focus:border-coral-300"
        />
      </motion.div>
    )},
  ];

  return (
    <main className="mx-auto w-full max-w-3xl px-4 py-5 sm:px-6 lg:px-8">
      <motion.div className="space-y-5 sm:space-y-6 lg:space-y-8" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ duration: 0.4 }}>
        {/* Back & Header */}
        <div>
          <motion.div initial={{ opacity: 0, x: -10 }} animate={{ opacity: 1, x: 0 }} transition={{ duration: 0.3 }}>
            <Link href="/tasks" className="inline-flex items-center gap-1.5 text-sm font-medium text-neutral-500 hover:text-neutral-700 transition-colors">
              <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current stroke-[1.8]"><path d="M19 12H5M12 19l-7-7 7-7" /></svg>
              {tTasks("detail.backToTasks")}
            </Link>
          </motion.div>
          <FadeInUp className="mt-4">
            <p className="section-label text-coral-500">{tTasks("create.eyebrow")}</p>
            <h1 className="page-title mt-2">{tTasks("create.title")}</h1>
            <p className="mt-1 max-w-lg text-sm leading-6 text-neutral-500">{tTasks("create.subtitle")}</p>
          </FadeInUp>
        </div>

        {success ? (
          <motion.div
            className="rounded-soft border border-mint-100 bg-mint-50 px-6 py-10 text-center"
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            transition={{ type: "spring", stiffness: 200, damping: 25 }}
          >
            <motion.div
              className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-mint-100 text-mint-500"
              variants={successIconVariants}
              initial="hidden"
              animate="visible"
            >
              <svg viewBox="0 0 24 24" className="h-8 w-8 fill-none stroke-current stroke-[2.5]"><path d="M20 6L9 17l-5-5" /></svg>
            </motion.div>
            <motion.h2
              className="font-display text-xl font-semibold text-neutral-900"
              variants={successTextVariants}
              initial="hidden"
              animate="visible"
            >
              {tTasks("create.success")}
            </motion.h2>
            <motion.div variants={successTextVariants} initial="hidden" animate="visible">
              <Link href="/tasks/new">
                <motion.div whileHover={{ scale: 1.05 }} whileTap={{ scale: 0.95 }}>
                  <Button variant="soft" size="sm" className="mt-4">{tTasks("create.createAnother")}</Button>
                </motion.div>
              </Link>
            </motion.div>
          </motion.div>
        ) : (
          <motion.form
            onSubmit={onSubmit}
            className="space-y-5 sm:space-y-6 lg:space-y-8"
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.15, duration: 0.5 }}
          >
            {/* Title */}
            <motion.div className="space-y-2" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1, duration: 0.4 }}>
              <label className="text-xs font-medium text-neutral-600">{tTasks("create.taskTitle")}</label>
              <input
                type="text"
                value={title}
                onChange={(e) => setTitle(e.target.value)}
                placeholder={tTasks("create.titlePlaceholder")}
                required
                autoFocus
                className="w-full border-0 border-b-2 border-neutral-200 bg-transparent px-0 py-2.5 sm:py-3 font-display text-xl sm:text-2xl font-semibold tracking-tight text-neutral-900 outline-none transition-colors placeholder:text-neutral-300 focus:border-coral-300"
              />
            </motion.div>

            {/* Description */}
            <motion.div className="space-y-2" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15, duration: 0.4 }}>
              <label className="text-xs font-medium text-neutral-600">{tTasks("create.description")}</label>
              <Textarea
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                placeholder={tTasks("create.descriptionPlaceholder")}
                rows={3}
              />
            </motion.div>

            {/* Category */}
            <motion.div className="space-y-3" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2, duration: 0.4 }}>
              <label className="text-xs font-medium text-neutral-600">{tTasks("create.category")}</label>
              <div className="flex flex-wrap gap-1.5 sm:gap-2">
                {categories.map((cat, i) => (
                  <motion.button
                    key={cat.value}
                    type="button"
                    onClick={() => setSelectedCategory(selectedCategory === cat.value ? "" : cat.value)}
                    className={cn(
                      "rounded-pill border px-2.5 sm:px-4 py-1.5 sm:py-2 text-[11px] sm:text-xs font-medium transition-all duration-200",
                      selectedCategory === cat.value ? cat.color + " ring-2 ring-offset-1 ring-coral-200" : "border-border-light bg-white text-neutral-500 hover:border-neutral-300"
                    )}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.25 + i * 0.04, duration: 0.3 }}
                    whileHover={{ y: -2, scale: 1.02 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    {cat.label}
                  </motion.button>
                ))}
              </div>
            </motion.div>

            {/* Duration presets */}
            <motion.div className="space-y-3" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25, duration: 0.4 }}>
              <label className="text-xs font-medium text-neutral-600">{tTasks("create.duration")}</label>
              <div className="flex flex-wrap gap-1.5 sm:gap-2">
                {durationPresets.map((preset, i) => (
                  <motion.button
                    key={preset.value}
                    type="button"
                    onClick={() => { setSelectedDuration(preset.value); setShowCustomDuration(false); }}
                    className={cn(
                      "rounded-pill border px-2.5 sm:px-4 py-1.5 sm:py-2 text-[11px] sm:text-xs font-medium transition-all duration-200",
                      selectedDuration === preset.value && !showCustomDuration
                        ? "border-coral-200 bg-coral-50 text-coral-600"
                        : "border-border-light bg-white text-neutral-500 hover:border-neutral-300"
                    )}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.3 + i * 0.04, duration: 0.3, type: "spring", stiffness: 200 }}
                    whileHover={{ y: -2 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    {tTasks(`create.${preset.labelKey}`)}
                  </motion.button>
                ))}
                <motion.button
                  type="button"
                  onClick={() => setShowCustomDuration(true)}
                  className={cn(
                    "rounded-pill border px-2.5 sm:px-4 py-1.5 sm:py-2 text-[11px] sm:text-xs font-medium transition-all duration-200",
                    showCustomDuration ? "border-coral-200 bg-coral-50 text-coral-600" : "border-border-light bg-white text-neutral-500 hover:border-neutral-300"
                  )}
                  initial={{ opacity: 0, scale: 0.9 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ delay: 0.5, duration: 0.3 }}
                  whileHover={{ y: -2 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {tTasks("create.durationCustom")}
                </motion.button>
              </div>
              <AnimatePresence>
                {showCustomDuration && (
                  <motion.div
                    initial={{ opacity: 0, height: 0, marginTop: 0 }}
                    animate={{ opacity: 1, height: "auto", marginTop: 12 }}
                    exit={{ opacity: 0, height: 0, marginTop: 0 }}
                    transition={{ duration: 0.3, ease: [0.25, 0.1, 0.25, 1] }}
                  >
                    <div className="flex items-center gap-3">
                      <Input
                        type="number"
                        min={1}
                        placeholder={tTasks("create.durationCustomPlaceholder")}
                        value={customDuration}
                        onChange={(e) => setCustomDuration(e.target.value)}
                        className="w-40"
                      />
                      <span className="text-xs text-neutral-400">minutes</span>
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>

            {/* Task Type */}
            <motion.div className="space-y-3" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.275, duration: 0.4 }}>
              <label className="text-xs font-medium text-neutral-600">{tTasks("create.taskType")}</label>
              <div className="flex flex-wrap gap-2">
                {[{value:"scheduled",labelKey:"taskTypeScheduled"},{value:"flexible",labelKey:"taskTypeFlexible"}].map((opt) => (
                  <motion.button
                    key={opt.value}
                    type="button"
                    onClick={() => setSelectedTaskType(opt.value)}
                    className={cn(
                      "rounded-pill border px-4 py-2 text-xs font-medium transition-all duration-200",
                      selectedTaskType === opt.value
                        ? opt.value === "flexible"
                          ? "border-lavender-200 bg-lavender-50 text-lavender-600"
                          : "border-coral-200 bg-coral-50 text-coral-600"
                        : "border-border-light bg-white text-neutral-500 hover:border-neutral-300"
                    )}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    whileHover={{ y: -2 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    {tTasks(`create.${opt.labelKey}`)}
                  </motion.button>
                ))}
              </div>
              {selectedTaskType === "flexible" && (
                <motion.p
                  className="text-xs text-lavender-500"
                  initial={{ opacity: 0, y: -5 }}
                  animate={{ opacity: 1, y: 0 }}
                >
                  {tTasks("create.flexibleHint")}
                </motion.p>
              )}
            </motion.div>

            {/* Start Time */}
            <motion.div className="space-y-2" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.4 }}>
              <label className="text-xs font-medium text-neutral-600">{tTasks("create.startTime")}</label>
              <TimePicker value={selectedStartTime} onChange={setSelectedStartTime} />
            </motion.div>

            {/* Deadline quick picks */}
            <motion.div className="space-y-3" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.3, duration: 0.4 }}>
              <label className="text-xs font-medium text-neutral-600">{tTasks("create.deadline")}</label>
              <div className="flex flex-wrap gap-1.5 sm:gap-2">
                {["today", "tomorrow", "weekend", "nextWeek"].map((option, i) => (
                  <motion.button
                    key={option}
                    type="button"
                    onClick={() => { setSelectedDeadline(getDateForOption(option)); setShowCustomDate(false); }}
                    className={cn(
                      "rounded-pill border px-2.5 sm:px-4 py-1.5 sm:py-2 text-[11px] sm:text-xs font-medium transition-all duration-200",
                      selectedDeadline === getDateForOption(option) && !showCustomDate
                        ? "border-coral-200 bg-coral-50 text-coral-600"
                        : "border-border-light bg-white text-neutral-500 hover:border-neutral-300"
                    )}
                    initial={{ opacity: 0, y: 8 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ delay: 0.35 + i * 0.04, duration: 0.3 }}
                    whileHover={{ y: -2 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    {tTasks(`create.deadline${option.charAt(0).toUpperCase() + option.slice(1)}`)}
                  </motion.button>
                ))}
                <motion.button
                  type="button"
            onClick={() => setShowCustomDate(true)}
            className={cn(
              "rounded-pill border px-2.5 sm:px-4 py-1.5 sm:py-2 text-[11px] sm:text-xs font-medium transition-all duration-200",
              showCustomDate ? "border-coral-200 bg-coral-50 text-coral-600" : "border-border-light bg-white text-neutral-500 hover:border-neutral-300"
            )}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.5, duration: 0.3 }}
                  whileHover={{ y: -2 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {tTasks("create.deadlineChoose")}
                </motion.button>
                <motion.button
                  type="button"
                  onClick={() => { setSelectedDeadline(""); setShowCustomDate(false); }}
                  className={cn(
                    "rounded-pill border px-2.5 sm:px-4 py-1.5 sm:py-2 text-[11px] sm:text-xs font-medium transition-all duration-200",
                    !selectedDeadline && !showCustomDate ? "border-coral-200 bg-coral-50 text-coral-600" : "border-border-light bg-white text-neutral-500 hover:border-neutral-300"
                  )}
                  initial={{ opacity: 0, y: 8 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.55, duration: 0.3 }}
                  whileHover={{ y: -2 }}
                  whileTap={{ scale: 0.95 }}
                >
                  {tCommon("none")}
                </motion.button>
              </div>
              <AnimatePresence>
                {showCustomDate && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: "auto" }}
                    exit={{ opacity: 0, height: 0 }}
                    transition={{ duration: 0.3 }}
                  >
                    <Input
                      type="date"
                      value={selectedDeadline}
                      onChange={(e) => setSelectedDeadline(e.target.value)}
                      className="w-48"
                    />
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>

            {/* Priority */}
            <motion.div className="space-y-3" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.35, duration: 0.4 }}>
              <label className="text-xs font-medium text-neutral-600">{tTasks("create.priority")}</label>
              <div className="flex flex-wrap gap-1.5 sm:gap-2">
                {priorityOptions.map((opt, i) => (
                  <motion.button
                    key={opt.value}
                    type="button"
                    onClick={() => setSelectedPriority(opt.value)}
                    className={cn(
                      "rounded-pill border px-2.5 sm:px-4 py-1.5 sm:py-2 text-[11px] sm:text-xs font-medium transition-all duration-200",
                      selectedPriority === opt.value
                        ? "border-coral-200 bg-coral-50 text-coral-600"
                        : "border-border-light bg-white text-neutral-500 hover:border-neutral-300"
                    )}
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    transition={{ delay: 0.4 + i * 0.05, duration: 0.3 }}
                    whileHover={{ y: -2 }}
                    whileTap={{ scale: 0.95 }}
                  >
                    {tTasks(`create.${opt.labelKey}`)}
                  </motion.button>
                ))}
              </div>
            </motion.div>

            {/* Labels (tags) */}
            <motion.div className="space-y-3" initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4, duration: 0.4 }}>
              <label className="text-xs font-medium text-neutral-600">{tTasks("create.labels")}</label>
              <div className="flex flex-wrap gap-2">
                <AnimatePresence>
                  {tags.map((tag) => (
                    <motion.span
                      key={tag}
                      className="inline-flex items-center gap-1.5 rounded-pill bg-coral-50 px-3 py-1.5 text-xs font-medium text-coral-600"
                      initial={{ opacity: 0, scale: 0.8 }}
                      animate={{ opacity: 1, scale: 1 }}
                      exit={{ opacity: 0, scale: 0.8 }}
                      transition={{ duration: 0.2 }}
                    >
                      {tag}
                      <button type="button" onClick={() => removeTag(tag)} className="text-coral-400 hover:text-coral-600">
                        <svg viewBox="0 0 12 12" className="h-3 w-3 fill-current"><path d="M2.22 2.22a.75.75 0 011.06 0L6 4.94l2.72-2.72a.75.75 0 111.06 1.06L7.06 6l2.72 2.72a.75.75 0 11-1.06 1.06L6 7.06l-2.72 2.72a.75.75 0 01-1.06-1.06L4.94 6 2.22 3.28a.75.75 0 010-1.06z" /></svg>
                      </button>
                    </motion.span>
                  ))}
                </AnimatePresence>
              </div>
              <div className="flex gap-2">
                <Input
                  value={tagInput}
                  onChange={(e) => setTagInput(e.target.value)}
                  onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); addTag(tagInput); } }}
                  placeholder={tTasks("create.labelsPlaceholder")}
                  className="flex-1"
                />
                <motion.div whileHover={{ scale: 1.02 }} whileTap={{ scale: 0.96 }}>
                  <Button type="button" variant="secondary" size="sm" onClick={() => addTag(tagInput)} disabled={!tagInput.trim()}>Add</Button>
                </motion.div>
              </div>
            </motion.div>

            {/* Error */}
            <AnimatePresence>
              {error && (
                <motion.p
                  className="rounded-soft border border-coral-100 bg-coral-50 px-4 py-3 text-sm text-coral-600"
                  initial={{ opacity: 0, y: -10, scale: 0.97 }}
                  animate={{ opacity: 1, y: 0, scale: 1 }}
                  exit={{ opacity: 0, y: -10, scale: 0.97 }}
                  transition={{ duration: 0.3 }}
                >
                  {error}
                </motion.p>
              )}
            </AnimatePresence>

            {/* Submit */}
            <motion.div
              className="flex flex-col xs:flex-row items-stretch xs:items-center gap-3 pt-4 border-t border-border-light"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.45, duration: 0.4 }}
            >
              <motion.div whileHover={{ scale: 1.03 }} whileTap={{ scale: 0.97 }}>
                <Button disabled={loading || !title.trim()} type="submit" size="lg" className="w-full xs:w-auto">
                  {loading ? tTasks("create.submitting") : tTasks("create.submit")}
                </Button>
              </motion.div>
              <Link href="/tasks"><Button type="button" variant="ghost" size="lg" className="w-full xs:w-auto">{tTasks("detail.backToTasks")}</Button></Link>
            </motion.div>
          </motion.form>
        )}
      </motion.div>
    </main>
  );
}
