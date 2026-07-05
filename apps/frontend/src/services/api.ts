import { ApiError } from "@/lib/api-error";

const baseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://localhost:8000/api/v1";

const authPathsWithoutAutoRefresh = new Set(["/auth/login", "/auth/register", "/auth/logout", "/auth/refresh"]);

async function rawFetch(path: string, init: RequestInit = {}): Promise<Response> {
  return fetch(`${baseUrl}${path}`, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    },
    ...init,
  });
}

async function refreshSession(): Promise<boolean> {
  const response = await rawFetch("/auth/refresh", { method: "POST" });
  return response.ok;
}

export async function apiFetch<T>(path: string, init: RequestInit = {}, retryOnUnauthorized = true): Promise<T> {
  const response = await rawFetch(path, init);

  if (response.status === 401 && retryOnUnauthorized && !authPathsWithoutAutoRefresh.has(path)) {
    const refreshed = await refreshSession();
    if (refreshed) {
      return apiFetch<T>(path, init, false);
    }
  }

  if (!response.ok) {
    const payload = (await response.json().catch(() => null)) as { error_code?: string; message?: string; detail?: string } | null;
    const errorCode = payload?.error_code ?? payload?.detail ?? "REQUEST_FAILED";
    throw new ApiError(errorCode, response.status);
  }

  if (response.status === 204) {
    return undefined as T;
  }

  return (await response.json()) as T;
}
