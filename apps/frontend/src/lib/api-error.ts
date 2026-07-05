export class ApiError extends Error {
  code: string;
  status: number;

  constructor(code: string, status: number) {
    super(code);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
  }
}

const supportedErrorCodes = new Set([
  "AUTH_UNAUTHORIZED",
  "AUTH_INVALID_CREDENTIALS",
  "AUTH_EMAIL_ALREADY_EXISTS",
  "AUTH_INVALID_REFRESH_TOKEN",
  "TASK_NOT_FOUND",
  "TASK_ALREADY_COMPLETED",
  "DAILY_PLAN_NOT_FOUND",
  "VALIDATION_ERROR",
  "TASK_TIME_CONFLICT",
  "INTERNAL_SERVER_ERROR",
  "REQUEST_FAILED",
  "HTTP_ERROR",
]);

export function getErrorMessage(error: unknown, t: (key: string) => string): string {
  if (error instanceof ApiError) {
    const key = supportedErrorCodes.has(error.code) ? error.code : "REQUEST_FAILED";
    return t(key);
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return t("REQUEST_FAILED");
}
