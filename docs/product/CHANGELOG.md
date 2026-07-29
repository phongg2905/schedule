# Changelog

## 2026-07-29 - Documentation aligned with current RC1 scope

### Changed

- README current status updated to reflect RC1 hardening and QA instead of older phase wording
- ML plan top summary now separates current state from historical audit notes
- Phase 6.5 hardening doc wording updated to reference RC1 explicitly

## 2026-07-01 - Internationalization baseline added

### Added

- next-intl integrated for global English and Vietnamese UI support
- reusable language switcher added with local guest persistence and authenticated server sync
- backend preference model split to keep language separate from working schedule settings
- AI context now carries preferred language and prompt instructions preserve JSON schema
- frontend user-facing strings replaced with translation keys and locale-aware date formatting

## 2026-07-01 - Phase 6.5 hardening started

### Added

- Phase 6.5 hardening scope documented with manual QA, error flow, loading state, audit, security, performance, and release criteria
- scaffolded AI endpoints aligned with real behavior instead of placeholder responses
- today screen loading and double-action protection hardened

## 2026-07-01 - Phase 6 progress 4

### Added

- daily progress actions completed for complete, skip, delay, and move flows
- AI adjustment flow completed with structured request schema and suggestion persistence
- insight summary completed with day summary persistence and event tracking
- today screen now shows progress actions, AI adjustment input, and insight summary
- backend tests expanded to cover daily progress, AI adjustment, and insight flow

## 2026-07-01 - Phase 6 progress 3

### Added

- AI daily plan generation completed with provider abstraction and local fallback
- AI explanation endpoint completed for "why this order" questions
- today screen now supports both rule-based and AI plan generation actions
- AI daily plan tests now pass in offline development mode

## 2026-07-01 - Phase 6 progress 2

### Added

- Working schedule and preferences entity plus settings page completed
- rule-based daily planner completed with task ordering, working hours, lunch break, and day off handling
- daily plan generation now returns schedule items and explanation text to the frontend
- backend and frontend verified after the planner changes

## 2026-07-01 - Phase 6 progress

### Added

- Authentication slice completed with register, login, refresh rotation, logout, and protected routes
- Task CRUD slice completed with deadline, tags, completed_at, and soft delete support
- Working Schedule & Preferences slice completed with settings page and persisted schedule preferences
- backend and frontend verified again after the MVP slice changes

## 2026-07-01 - Phase 6 started

### Added

- Phase 6 reframed as MVP Feature Development
- milestone model introduced for M0-M3 release grouping
- vertical slice order frozen by user value instead of layer order
- authentication epic broken down into issues with acceptance criteria and estimates
- working schedule and preferences inserted before rule-based planning

## 2026-06-30 - Phase 5 completed

### Added

- project bootstrap with Next.js, FastAPI, PostgreSQL, Redis, and Docker Compose
- backend foundation with clean architecture, config, middleware, logging, auth, and SQLAlchemy
- frontend foundation with App Router, Tailwind, reusable layout, and auth-aware pages
- smoke tests for backend app wiring and health routes
- verified frontend production build and backend pytest baseline

## 2026-06-30 - Phase 5 started

### Added

- renamed Phase 5 to Foundation Implementation
- defined sprint breakdown for bootstrap, backend foundation, frontend foundation, and vertical slices
- prioritized core data flow validation before deep AI integration

## 2026-06-30 - Phase 4 completed

### Added

- system architecture blueprint with frontend, backend, data, AI, deployment, and security docs
- additional architecture docs for database design, testing strategy, observability, error handling, environments, and ADRs

## 2026-06-30 - Phase 3 started

### Added

- data architecture blueprint with domain model, event model, AI context, and database design
- event-first thinking for behavior tracking and AI memory

## 2026-06-30 - Phase 2 completed

### Added

- UX blueprint with persona, journey, user story, flow, IA, feature specification, and wireframe
- core flow centered design for planning, adjustment, and completion

## 2026-06-30

### Added

- product foundation with vision, manifesto, goals, MVP scope, and roadmap baseline
