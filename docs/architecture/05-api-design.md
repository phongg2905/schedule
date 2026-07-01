# API Design

## Purpose

Chốt danh sách API cần có trước khi triển khai backend.

## API principles

- resource-oriented
- versionable
- explicit payloads
- clear error responses
- generate OpenAPI from FastAPI as source for Swagger docs

## Base path

- prefix all endpoints with `/api/v1`

## Core endpoints

### Auth

- `POST /api/v1/auth/register`
- `POST /api/v1/auth/login`
- `POST /api/v1/auth/refresh`
- `POST /api/v1/auth/logout`
- `GET /api/v1/auth/me`

### Tasks

- `GET /api/v1/tasks`
- `POST /api/v1/tasks`
- `GET /api/v1/tasks/{id}`
- `PATCH /api/v1/tasks/{id}`
- `DELETE /api/v1/tasks/{id}`

### Daily plans

- `GET /api/v1/daily-plans/today`
- `POST /api/v1/daily-plans/generate`
- `GET /api/v1/daily-plans/{id}`
- `PATCH /api/v1/daily-plans/{id}`
- `POST /api/v1/daily-plans/{id}/apply`
- `POST /api/v1/daily-plans/{id}/complete`

### Schedules

- `GET /api/v1/schedules/today`
- `GET /api/v1/schedules/week`
- `PATCH /api/v1/schedules/{id}`
- `GET /api/v1/schedules/{id}`

### AI

- `POST /api/v1/ai/adjust`
- `POST /api/v1/ai/regenerate`
- `POST /api/v1/ai/summarize`

### Events and feedback

- `POST /api/v1/events`
- `POST /api/v1/feedback`
- `GET /api/v1/events`

### Health

- `GET /api/v1/health`
- `GET /api/v1/health/ready`

## API rules

- all write APIs must emit event(s)
- daily plan APIs must return plan state and explanation
- AI endpoints must accept context window hints where needed
- GET endpoints must not trigger hidden writes

## Endpoint contract notes

### `POST /api/v1/auth/login`

Request body:

- email
- password

Response:

- access token/session indicator
- user profile summary

Validation:

- email required
- password required

Authorization:

- public

### `POST /api/v1/tasks`

Request body:

- title
- description optional
- due_date optional
- priority optional
- estimated_duration optional

Response:

- created task
- emitted event reference

Validation:

- title required

Authorization:

- authenticated user

### `POST /api/v1/daily-plans/generate`

Request body:

- plan_date
- context_window_type
- trigger_source

Response:

- daily plan
- explanation
- context snapshot reference

Validation:

- plan_date required
- context window type must be supported

Authorization:

- authenticated user

### `POST /api/v1/ai/adjust`

Request body:

- daily_plan_id
- change_description

Response:

- updated suggestion or adjusted plan
- explanation

Error cases:

- no plan found
- insufficient context
- AI provider failure
