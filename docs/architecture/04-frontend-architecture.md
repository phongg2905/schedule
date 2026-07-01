# Frontend Architecture

## Purpose

Xác định cách tổ chức Next.js frontend để UI bám Core Flow và không phình feature logic vào component.

## Suggested app structure

```text
app/
features/
components/
hooks/
services/
lib/
types/
```

## Rules

- `app/` owns routes and page composition
- `features/` owns product areas like authentication, dashboard, tasks, schedules, planning, ai-assistant, settings
- `components/` owns reusable UI building blocks
- `hooks/` owns shared client behavior
- `services/` owns API calls and adapters
- `lib/` owns utility helpers
- `types/` owns shared TypeScript types

## Feature split

```text
features/
  authentication/
  dashboard/
  tasks/
  schedules/
  planning/
  ai-assistant/
  settings/
```

## Component ownership

- use `features/*` for screen-specific logic
- use `components/*` for generic reusable UI
- do not move business rules into presentational components

## Routing

- `app/` should define route segments
- protected routes must redirect unauthenticated users to login
- Today is the default landing page after authentication

## State management

- server state should be fetched and cached separately from UI state
- client-only UI state stays local unless it must survive navigation
- use a dedicated store only for cross-screen client state

## API client

- place API client logic in `services/`
- use typed request/response contracts from `types/`
- never call `fetch` directly inside multiple unrelated components if the same adapter is needed elsewhere

## Auth state

- store auth session in secure HTTP-only cookies if supported by backend
- client should derive auth status from backend session endpoint
- do not rely on localStorage for sensitive auth tokens

## Forms and validation

- form validation should run before submit
- backend validation remains the source of truth
- reuse schema definitions where possible

## UI states

- every major screen must define loading, empty, success and error states
- AI generation screens must show progress and retry affordances

## Screen mapping

- `Today` is the default landing page after login
- `Tasks` handles task CRUD
- `Calendar` handles day/week views and direct edits
- `Insights` shows progress and summaries
- `Settings` handles profile and preferences

## State rules

- keep server state separate from local UI state
- loading and error states must be explicit
- AI generation states must be visible in the UI
