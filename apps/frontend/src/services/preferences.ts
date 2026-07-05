import { apiFetch } from "@/services/api";

export type Language = "en" | "vi";

export type SchedulePreferences = {
  timezone: string;
  work_start_time: string;
  work_end_time: string;
  lunch_start_time: string;
  lunch_end_time: string;
  day_offs: string[];
  focus_hours: string[];
};

export async function fetchLanguagePreference() {
  return apiFetch<{ language: Language }>("/settings/preferences/language");
}

export async function updateLanguagePreference(language: Language) {
  return apiFetch<{ language: Language }>("/settings/preferences/language", {
    method: "PUT",
    body: JSON.stringify({ language }),
  });
}

export async function fetchSchedulePreferences() {
  return apiFetch<SchedulePreferences>("/settings/preferences");
}

export async function updateSchedulePreferences(payload: SchedulePreferences) {
  return apiFetch<SchedulePreferences>("/settings/preferences", {
    method: "PUT",
    body: JSON.stringify(payload),
  });
}
