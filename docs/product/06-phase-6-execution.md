# Phase 6 - MVP Feature Development

## Goal

Build the MVP through vertical slices that deliver user value, are self-testable, and can be released as usable milestones.

## Operating Rules

1. Every vertical slice must create user value.
2. Every slice must have a clear Definition of Done.
3. Every slice must be self-used before it is marked done.
4. No issue may be too large. If a task feels like more than 1-3 hours, split it.

## Milestones

### M0

- Authentication
- Task CRUD
- Working Schedule & Preferences

### M1

- Daily Plan Rule-based

### M2

- AI Generate
- AI Explanation

### M3

- Daily Progress
- AI Adjustment
- Insight

## Slice Order

1. Authentication
2. Task CRUD
3. Working Schedule & Preferences
4. Daily Plan Rule-based
5. AI Generate Daily Plan
6. AI Explanation
7. Daily Progress
8. AI Adjustment
9. Insight

## Issue Template

Use this structure for every issue:

- Goal
- Acceptance Criteria
- Dependencies
- Estimate
- Status

## Authentication Epic Breakdown

| Issue | Goal | Acceptance Criteria | Dependencies | Estimate | Status |
| --- | --- | --- | --- | --- | --- |
| A1 | Backend - Register API | User can register, password is hashed, validation works | Auth domain skeleton | 1-2h | Todo |
| A2 | Backend - Login API | User can login and receive auth cookies/tokens | A1 | 1-2h | Todo |
| A3 | Backend - Refresh Token | Session can be refreshed and rotated | A2 | 1-2h | Todo |
| A4 | Backend - Logout | Session can be invalidated and cookies cleared | A3 | 1h | Todo |
| A5 | Frontend - Register Page | User can create account from UI | A1 | 1-2h | Todo |
| A6 | Frontend - Login Page | User can login from UI | A2 | 1-2h | Todo |
| A7 | Frontend - Auth Guard | Protected routes redirect correctly | A2, A3 | 1-2h | Todo |
| A8 | Integration Test | Auth flow is covered by tests | A1-A7 | 1-2h | Todo |
| A9 | Manual QA | Authentication works end to end | A1-A8 | 1h | Todo |
| A10 | Documentation Update | Docs reflect implemented auth behavior | A1-A9 | 30m | Todo |

## Release Milestones

- M0 is releasable once Authentication, Task CRUD, and Working Schedule & Preferences are usable end to end.
- M1 is releasable once the rule-based daily planner can build a useful schedule from real user data.
- M2 is releasable once AI generation and explanation are stable and validated.
- M3 is releasable once progress, adjustment, and insight close the daily feedback loop.
