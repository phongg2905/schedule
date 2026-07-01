# Database Design

## Purpose

Chuyển domain model và event model thành schema có thể triển khai thật.

## Design principles

- normalize core entities
- keep event log append-only
- separate current state from history
- use foreign keys for critical references
- support analytics queries without damaging OLTP paths

## Core tables

### users

- id
- email
- name
- timezone
- created_at
- updated_at

### tasks

- id
- user_id
- title
- description
- status
- priority
- due_date
- estimated_duration
- created_at
- updated_at

### schedules

- id
- user_id
- daily_plan_id nullable
- schedule_date
- schedule_type
- source
- created_at
- updated_at

### daily_plans

- id
- user_id
- plan_date
- status
- source
- context_snapshot_id nullable
- created_at
- updated_at

### schedule_items

- id
- schedule_id
- task_id nullable
- start_time
- end_time
- label
- status
- source
- created_at
- updated_at

### ai_suggestions

- id
- user_id
- daily_plan_id nullable
- suggestion_type
- context_snapshot_id
- explanation
- status
- created_at
- updated_at

### feedback

- id
- user_id
- target_type
- target_id
- rating
- note
- created_at

### activity_events

- id
- user_id
- event_type
- entity_type
- entity_id
- source
- payload
- occurred_at

### context_snapshots

- id
- user_id
- snapshot_type
- context_payload
- created_at

### day_summaries

- id
- user_id
- summary_date
- summary_payload
- created_at

## Relationships

- users 1:n tasks
- users 1:n daily_plans
- users 1:n schedules
- daily_plans 1:n schedules
- schedules 1:n schedule_items
- tasks 1:n schedule_items
- users 1:n ai_suggestions
- ai_suggestions 1:1 context_snapshots
- ai_suggestions n:1 daily_plans
- users 1:n feedback
- users 1:n activity_events
- users 1:n day_summaries

## Audit and analytics

`activity_events` is the primary audit log.

`context_snapshots` stores what AI saw at generation time.

`day_summaries` stores end-of-day rollups for future planning.

## Query strategy

- current state reads from tasks, schedules and schedule_items
- historical behavior reads from activity_events
- AI debugging reads from ai_suggestions + context_snapshots
- product analytics reads from event aggregates
- daily planning reads from daily_plans as the top-level aggregate

## MVP notes

- no need for over-normalized ML tables yet
- keep schema simple enough to ship
- preserve expansion room for future memory and personalization
