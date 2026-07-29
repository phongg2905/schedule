# Phase 6.5 - Hardening

## Goal

Stabilize the MVP before RC1. No new feature work.

## Scope

- manual QA on the full user flow
- AI failure and fallback review
- loading, empty, and error state review
- event audit review
- performance review
- security review
- documentation and release criteria

## Manual QA Flow

1. Register
2. Login
3. Create task
4. Generate daily plan
5. Complete a task
6. Delay a task
7. Move a task
8. Generate insight summary

## Release Criteria

- Authentication passes end to end
- Task CRUD passes end to end
- Daily plan generation passes end to end
- Daily progress passes end to end
- AI adjustment passes end to end
- Insight summary passes end to end
- Backend tests pass
- Frontend build passes
- README updated
- Changelog updated
- No critical bug remains open

## Notes

- Do not add new product features in this phase.
- If a gap appears, document it as an issue instead of expanding scope.
