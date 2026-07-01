# Folder Structure

## Goal

Chốt cấu trúc thư mục đủ sạch để implementation không phải tranh luận lại quá nhiều.

## Proposed structure

```text
apps/
  frontend/
  backend/

packages/
  shared/
  ui/
  types/

docs/
  product/
  design/
  data/
  architecture/

infra/
  docker/
  compose/
  nginx/
```

## Rules

- `apps/frontend` contains Next.js frontend
- `apps/backend` contains FastAPI backend
- `packages/shared` contains shared domain helpers and utilities
- `packages/ui` contains reusable UI components if needed
- `packages/types` contains shared type definitions and API contracts
- `docs/*` remains the source of truth for decisions
- `infra/*` contains runtime and deployment assets only

## Backend target structure

```text
src/
  auth/
  users/
  tasks/
  daily_plans/
  schedules/
  ai/
  notifications/
  events/
  common/
  config/
```

## Frontend target structure

```text
src/
  app/
  components/
  features/
  services/
  hooks/
  stores/
  types/
  utils/
```

## MVP note

If the repo starts as a single repository first, the structure above still acts as the target layout.
