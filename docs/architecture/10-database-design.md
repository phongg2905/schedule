# Database Design

## Purpose

Mô tả database ở mức triển khai kỹ thuật cho Phase 4.

## Database choice

- PostgreSQL

## Design principles

- current state and history should be separated
- event log is append-only
- foreign keys must exist for critical relationships
- indexes should support common lookup paths
- soft delete only when product behavior requires recovery

## Core tables

### users

- id PK
- email unique
- password_hash
- name
- timezone
- role
- created_at
- updated_at
- deleted_at nullable

### refresh_tokens

- id PK
- user_id FK
- token_hash
- expires_at
- revoked_at nullable
- created_at

### tasks

- id PK
- user_id FK
- daily_plan_id FK nullable
- title
- description nullable
- status
- priority nullable
- due_date nullable
- estimated_duration nullable
- created_at
- updated_at
- deleted_at nullable

### daily_plans

- id PK
- user_id FK
- plan_date
- status
- source
- context_snapshot_id FK nullable
- created_at
- updated_at

### schedules

- id PK
- daily_plan_id FK
- user_id FK
- schedule_date
- schedule_type
- source
- created_at
- updated_at

### schedule_items

- id PK
- schedule_id FK
- task_id FK nullable
- start_time
- end_time
- label
- status
- source
- created_at
- updated_at

### ai_suggestions

- id PK
- user_id FK
- daily_plan_id FK nullable
- context_snapshot_id FK
- suggestion_type
- explanation
- status
- created_at
- updated_at

### feedback

- id PK
- user_id FK
- target_type
- target_id
- rating
- note nullable
- created_at

### activity_events

- id PK
- user_id FK nullable
- event_type
- entity_type
- entity_id
- source
- payload jsonb
- occurred_at

### context_snapshots

- id PK
- user_id FK
- snapshot_type
- context_payload jsonb
- created_at

### day_summaries

- id PK
- user_id FK
- summary_date
- summary_payload jsonb
- created_at

## Relationships

- users 1:n tasks
- users 1:n daily_plans
- daily_plans 1:n schedules
- schedules 1:n schedule_items
- tasks 1:n schedule_items
- users 1:n ai_suggestions
- users 1:n feedback
- users 1:n activity_events
- users 1:n context_snapshots
- users 1:n day_summaries

## Indexes

- users.email unique index
- tasks.user_id + status
- tasks.user_id + due_date
- daily_plans.user_id + plan_date unique index
- schedules.daily_plan_id
- activity_events.user_id + occurred_at
- ai_suggestions.user_id + created_at

## Constraints

- one daily plan per user per date
- schedule item time range must be valid
- event payload should never be null
- refresh token hash must be unique

## Migration strategy

- use incremental migrations
- keep schema changes backward compatible when possible
- never edit old migrations after they are applied in shared environments

