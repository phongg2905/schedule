import { apiFetch } from "@/services/api";

export type User = {
  id: string;
  email: string;
  name: string;
  timezone: string;
  role: string;
};

export async function fetchMe(): Promise<User> {
  return apiFetch<User>("/auth/me");
}
