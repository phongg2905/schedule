# Backend Architecture

## Purpose

Xác định cách tổ chức backend FastAPI để giữ sạch business logic, data access, and AI orchestration.

## Layer model

```text
API
  ↓
Controller / Route
  ↓
Service
  ↓
Repository
  ↓
Database
```

## Responsibilities

### API layer

- validate request
- map DTOs
- return HTTP response

### Service layer

- business rules
- orchestration
- AI triggering
- event creation

### Repository layer

- read/write database
- keep persistence concerns isolated

## Architecture rule

Controller → Application Service → Domain/Business Logic → Repository/SQLAlchemy

## Module boundaries

### auth

- login, refresh, logout, session checking

### users

- profile and preference management

### tasks

- CRUD, completion, rescheduling

### daily_plans

- plan generation, apply, complete, summary state

### schedules

- calendar views and schedule mutations

### ai

- context building, prompt building, response parsing

### notifications

- future alerts and reminders

### events

- event append, event query, audit

### common

- exceptions, base schemas, utilities

### config

- settings, environment loading, feature flags

## Dependency rules

- routes do not call repositories directly
- repositories do not know about HTTP
- AI orchestration must depend on context builder, not raw controller data
- services should be stateless where possible
- DTO validation happens at the boundary
- transaction boundaries belong in service layer

## DTO and validation

- request DTOs use Pydantic models
- invalid input is rejected before business logic runs
- response DTOs should not leak persistence internals

## Transactions

- use transactions around multi-entity writes
- event writes and plan updates must stay consistent
- AI response persistence should be atomic with final validation

## Background jobs

- daily summary generation
- deferred analytics snapshot
- future notification jobs

## Error handling

- backend errors should be normalized into structured API error responses
- domain errors should not bubble as raw stack traces

## Logging and audit

- log request id, user id where available, operation name and outcome
- persist audit events in `activity_events`

## MVP note

Use clean boundaries, but do not over-abstract repository interfaces before they are needed.
