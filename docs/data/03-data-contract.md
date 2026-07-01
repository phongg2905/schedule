# Data Contract

## Purpose

Định nghĩa dữ liệu trao đổi giữa frontend, backend, event store và AI layer.

## Contract principles

- explicit over implicit
- typed payloads
- versioned contracts when needed
- no AI without context
- no context without source data
- contracts must preserve event category and source
- contracts must state which context window is being used

## Frontend to backend

### Create task

Input:

- title
- description
- due_date
- priority
- estimated_duration

Output:

- task object
- task_created event
- event source: `manual`

### Update schedule

Input:

- schedule_item_id
- time range
- priority
- reason

Output:

- updated schedule item
- schedule_item_updated event
- event source: `manual` or `ai`

### Submit feedback

Input:

- target_type
- target_id
- rating
- note

Output:

- saved feedback
- feedback_submitted event
- event source: `manual`

## Backend to AI

### AI schedule request

Input:

- user profile
- tasks for the day
- current schedule
- event history window
- recent feedback
- availability window
- current day context
- context window type
- trigger source

Output:

- proposed schedule
- explanation blocks
- rationale labels
- confidence hints
- context snapshot id
- daily plan id

## AI to backend

### AI schedule response

Required fields:

- suggestion_id
- mode
- items
- explanation
- context_snapshot_id
- source: `ai`
- daily_plan_id

### AI schedule failure

Required fields:

- error_code
- message
- retryable
- context_snapshot_id if available

## Context window contract

Mỗi request gửi sang AI phải khai báo window type rõ ràng:

- `today_open`
- `daily_generation`
- `adjustment`
- `summary`

Mỗi window type được phép lấy dữ liệu khác nhau. Không được dùng một prompt chung cho mọi trường hợp.

## Daily plan contract

Mỗi response tạo lịch phải xác định rõ:

- daily_plan_id
- plan_date
- schedule items belong to that plan
- accepted or rejected state of the generated plan

## Versioning rules

- contract changes must be backward-aware
- event names should not change casually
- context shape can expand, but core fields must stay stable
