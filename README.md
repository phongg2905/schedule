# AI Planner

AI Planner is an AI companion for planning, schedule adjustment, behavior tracking, and progress review.

## Current Status

- Phase 6.5: Hardening in progress
- Phase 5 foundation is complete and runnable
- Authentication, Task CRUD, Working Schedule & Preferences, Rule-based Daily Plan, AI Generate/Explain, Daily Progress, AI Adjustment, and Insight are implemented
- Internationalization baseline is implemented with English and Vietnamese support
- Product, UX, data, and architecture blueprints are the source of truth
- Persistence uses managed PostgreSQL on Supabase
- Schema changes are managed through Alembic migrations

## Product Positioning

- Not a Todo App
- Not a Calendar App
- Not a ChatGPT Clone
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

- The project does not ship with a local database
- Use the managed PostgreSQL connection from your deployment environment
- Apply schema changes with `cd apps/backend && alembic upgrade head`
- The application runtime reads `DATABASE_URL` from the environment
