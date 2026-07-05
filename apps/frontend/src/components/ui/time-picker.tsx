"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { cn } from "@/lib/cn";
import { Input } from "@/components/ui/input";

// ── Time slot presets (every 30 minutes from 06:00 to 22:00) ──

const TIME_SLOTS: string[] = [];
for (let h = 6; h <= 22; h++) {
  TIME_SLOTS.push(`${h.toString().padStart(2, "0")}:00`);
  if (h < 22) TIME_SLOTS.push(`${h.toString().padStart(2, "0")}:30`);
}

function formatDisplay(time: string): string {
  const [h, m] = time.split(":").map(Number);
  const period = h >= 12 ? "PM" : "AM";
  const displayH = h % 12 || 12;
  return `${displayH}:${m.toString().padStart(2, "0")} ${period}`;
}

function groupSlots(): Array<{ label: string; slots: string[] }> {
  return [
    { label: "Sáng", slots: TIME_SLOTS.filter((t) => {
      const h = parseInt(t);
      return h >= 6 && h < 12;
    })},
    { label: "Trưa", slots: TIME_SLOTS.filter((t) => {
      const h = parseInt(t);
      return h >= 12 && h < 13;
    })},
    { label: "Chiều", slots: TIME_SLOTS.filter((t) => {
      const h = parseInt(t);
      return h >= 13 && h < 18;
    })},
    { label: "Tối", slots: TIME_SLOTS.filter((t) => {
      const h = parseInt(t);
      return h >= 18;
    })},
  ];
}

type TimePickerProps = {
  value: string;
  onChange: (time: string) => void;
};

export function TimePicker({ value, onChange }: Readonly<TimePickerProps>) {
  const [showCustom, setShowCustom] = useState(false);
  const groups = groupSlots();

  return (
    <div className="space-y-3">
      {/* Preset slots grid */}
      <div className="space-y-3 max-h-[260px] overflow-y-auto pr-1">
        {groups.map((group) => (
          <div key={group.label}>
            <p className="text-[11px] font-semibold uppercase tracking-wider text-neutral-400 mb-1.5">
              {group.label}
            </p>
            <div className="flex flex-wrap gap-1.5">
              {group.slots.map((slot) => {
                const isSelected = value === slot && !showCustom;
                return (
                  <motion.button
                    key={slot}
                    type="button"
                    onClick={() => { setShowCustom(false); onChange(slot); }}
                    className={cn(
                      "rounded-pill border px-3 py-1.5 text-xs font-medium transition-colors duration-200",
                      isSelected
                        ? "border-coral-200 bg-coral-50 text-coral-600 shadow-[0_0_0_1px_rgba(255,122,92,0.15)]"
                        : "border-border-light bg-white text-neutral-500 hover:border-neutral-300 hover:bg-neutral-50"
                    )}
                    whileHover={{ y: -2, scale: 1.03 }}
                    whileTap={{ scale: 0.92 }}
                    animate={isSelected ? { scale: [1, 1.08, 1], transition: { duration: 0.3, ease: "easeOut" } } : {}}
                    layout
                  >
                    <span className="inline-flex items-center gap-1.5">
                      {isSelected && (
                        <motion.span
                          initial={{ scale: 0, rotate: -90 }}
                          animate={{ scale: 1, rotate: 0 }}
                          transition={{ type: "spring", stiffness: 400, damping: 15 }}
                        >
                          <svg viewBox="0 0 12 12" className="h-3 w-3 fill-coral-500">
                            <path d="M10.28 2.22a.75.75 0 010 1.06l-6 6a.75.75 0 01-1.06 0l-3-3a.75.75 0 011.06-1.06L3.75 7.69l5.47-5.47a.75.75 0 011.06 0z" />
                          </svg>
                        </motion.span>
                      )}
                      {formatDisplay(slot)}
                    </span>
                  </motion.button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      {/* Custom time toggle */}
      <div className="flex items-center gap-2 pt-1">
        <motion.button
          type="button"
          onClick={() => { setShowCustom(!showCustom); if (!showCustom) onChange(""); }}
          className={cn(
            "rounded-pill border px-3 py-1.5 text-xs font-medium transition-all duration-200",
            showCustom
              ? "border-coral-200 bg-coral-50 text-coral-600"
              : "border-border-light bg-white text-neutral-500 hover:border-neutral-300"
          )}
          whileHover={{ y: -1 }}
          whileTap={{ scale: 0.95 }}
        >
          <span className="inline-flex items-center gap-1">
            <svg viewBox="0 0 12 12" className="h-3 w-3 fill-none stroke-current stroke-[1.5]">
              <path d="M6 2.5v3.5l2.5 1.5" />
              <circle cx="6" cy="6" r="4.5" />
            </svg>
            Tuỳ chỉnh
          </span>
        </motion.button>
        {showCustom && <span className="text-xs text-neutral-400">Nhập giờ cụ thể</span>}
      </div>

      {/* Custom time input */}
      <AnimatePresence>
        {showCustom && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: "auto" }}
            exit={{ opacity: 0, height: 0 }}
            transition={{ duration: 0.2 }}
          >
            <Input
              type="time"
              value={value}
              onChange={(e) => onChange(e.target.value)}
              className="w-44"
            />
          </motion.div>
        )}
      </AnimatePresence>

      {/* Selected time display */}
      {value && !showCustom && (
        <motion.p
          className="text-xs font-medium text-coral-500"
          initial={{ opacity: 0, y: -5 }}
          animate={{ opacity: 1, y: 0 }}
        >
          Đã chọn: {formatDisplay(value)}
        </motion.p>
      )}
    </div>
  );
}
