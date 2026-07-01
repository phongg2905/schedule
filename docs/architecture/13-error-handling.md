# Error Handling

## Purpose

Chuẩn hóa cách hệ thống trả lỗi để frontend và backend không phải đoán cách xử lý.

## Error principles

- errors must be explicit
- errors must be machine-readable
- user-facing messages must be short and actionable
- do not leak stack traces

## Error categories

- validation error
- authentication error
- authorization error
- not found error
- conflict error
- AI provider error
- infrastructure error

## Backend error shape

```json
{
  "error_code": "TASK_NOT_FOUND",
  "message": "Task not found",
  "request_id": "req_123"
}
```

## AI-specific failures

- malformed output
- timeout
- provider unavailable
- unsafe content

## Fallback rules

- preserve user input
- allow manual editing
- allow retry when retryable
- do not block the app because AI failed

## Frontend behavior

- show inline validation for form errors
- show retry action for transient errors
- show fallback action when AI fails

