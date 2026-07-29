# AI Planner

AI Planner is an AI planning assistant for tasks, daily scheduling, progress tracking, and review.

## Current Status

- Core MVP features are implemented: authentication, task CRUD, working schedule and preferences, rule-based daily planning, AI generate and explain, daily progress, AI adjustment, insights, and ML monitoring
- Internationalization is wired in with English and Vietnamese support
- The project is in RC1 hardening and QA, with release readiness tracked in `docs/release/RC1-QA.md`
- Product, UX, data, and architecture docs are the source of truth for scope and behavior
- Runtime persistence uses PostgreSQL through environment configuration, and schema changes are managed with Alembic migrations

## Product Positioning

- Not a Todo app
- Not a Calendar app
- Not a generic ChatGPT clone
- AI recommends, never forces

## Core Documents

- [Product Vision](docs/product/01-product-vision.md)
- [Product Manifesto](docs/product/02-product-manifesto.md)
- [Product Goals](docs/product/03-product-goals.md)
- [MVP Scope](docs/product/04-mvp-scope.md)
- [Roadmap](docs/product/05-roadmap.md)
- [Phase 6 Execution](docs/product/06-phase-6-execution.md)
- [Changelog](docs/product/CHANGELOG.md)
- [Design Blueprint](docs/design/04-user-flow.md)
- [Data Blueprint](docs/data/01-domain-model.md)
- [Technical Blueprint](docs/architecture/01-system-overview.md)

## Working Principles

- Simple > Complex
- UX first
- Data first
- Build for version 3, ship version 1
- All major changes must be explained and documented

## Database Setup

- The project is configured through environment variables
- Use the PostgreSQL connection provided by your deployment or dev environment
- Apply schema changes with `cd apps/backend && alembic upgrade head`
- The application runtime reads `DATABASE_URL` from the environment
