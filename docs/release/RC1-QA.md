# RC1 QA Checklist

## Purpose

Use this document to run release-candidate QA before opening beta or shipping RC1.

## Current Validation Status

- Backend regression: PASS
- Frontend build exit-code confirmation: PENDING
- Browser-based manual QA: PENDING
- Critical/High bug triage: PENDING

## Release Metrics

| Metric | Target |
| --- | --- |
| Critical bugs | 0 |
| High bugs | 0 before RC |
| Medium bugs | <= 5 |
| Low bugs | Acceptable |
| Crash | 0 |
| Data corruption | 0 |
| API 500 in happy path | 0 |

## Test Run #1 - Happy Path

Goal: a new user can use AI Planner end to end without friction.

| ID | Step | Expected | Status | Issue |
| --- | --- | --- | --- | --- |
| TC-001 | Register | Account is created | Pending |  |
| TC-002 | Login | Session opens and user lands in app | Pending |  |
| TC-003 | Open Today | Today screen loads with current state | Pending |  |
| TC-004 | Create Task | Task is saved and listed | Pending |  |
| TC-005 | Generate Daily Plan | Plan is created and shown | Pending |  |
| TC-006 | Complete Task | Task and schedule update correctly | Pending |  |
| TC-007 | Delay Task | Task is deferred and tracked | Pending |  |
| TC-008 | Move Task | Task is moved to another day | Pending |  |
| TC-009 | Generate Summary | Insight appears and reflects progress | Pending |  |
| TC-010 | Logout | Session clears and user is redirected | Pending |  |
| TC-011 | Login Again | User returns without data loss | Pending |  |
| TC-012 | Verify Persistence | Data remains correct after re-login | Pending |  |

## Test Run #2 - Edge Cases

### Authentication

| ID | Scenario | Expected | Status | Issue |
| --- | --- | --- | --- | --- |
| TC-101 | Register with existing email | Validation or error message shown | Pending |  |
| TC-102 | Wrong password | Login fails safely | Pending |  |
| TC-103 | Expired token | Refresh flow or redirect works | Pending |  |
| TC-104 | Refresh multiple times | Token rotation stays stable | Pending |  |

### Task

| ID | Scenario | Expected | Status | Issue |
| --- | --- | --- | --- | --- |
| TC-201 | Empty title | Validation blocks save | Pending |  |
| TC-202 | Very long title | Validation blocks or truncates safely | Pending |  |
| TC-203 | Past deadline | Task still saves or warns clearly | Pending |  |
| TC-204 | Duration = 0 | Validation blocks save | Pending |  |
| TC-205 | Invalid priority | Validation blocks save | Pending |  |

### Planner

| ID | Scenario | Expected | Status | Issue |
| --- | --- | --- | --- | --- |
| TC-301 | No task | Empty state explains next action | Pending |  |
| TC-302 | 100 tasks | Generation remains usable | Pending |  |
| TC-303 | Empty schedule preferences | Defaults apply safely | Pending |  |
| TC-304 | Generate repeatedly | No duplicate corruption | Pending |  |

### Progress

| ID | Scenario | Expected | Status | Issue |
| --- | --- | --- | --- | --- |
| TC-401 | Complete twice | Second action is rejected or idempotent | Pending |  |
| TC-402 | Delay after complete | System prevents inconsistent state | Pending |  |
| TC-403 | Move to another day | Task state and history remain consistent | Pending |  |
| TC-404 | Skip then regenerate | Planner respects updated state | Pending |  |

## Test Run #3 - AI

| ID | Scenario | Expected | Status | Issue |
| --- | --- | --- | --- | --- |
| TC-501 | OpenAI timeout | Fallback or clear error shown | Pending |  |
| TC-502 | OpenAI returns invalid JSON | Response validation fails safely | Pending |  |
| TC-503 | No API key | Local fallback is used | Pending |  |
| TC-504 | Context too large | Request is limited or summarized | Pending |  |
| TC-505 | AI returns invalid schedule | Backend rejects unsafe output | Pending |  |

## Test Run #4 - Persistence

| ID | Scenario | Expected | Status | Issue |
| --- | --- | --- | --- | --- |
| TC-601 | Complete task | Task state is completed | Pending |  |
| TC-602 | Schedule item update | Matching item changes too | Pending |  |
| TC-603 | Event log | Event is emitted and queryable | Pending |  |
| TC-604 | Summary update | DaySummary reflects the day | Pending |  |
| TC-605 | Insight check | Insight matches stored events | Pending |  |

## Test Run #5 - UX

| ID | Question | Expected | Status | Issue |
| --- | --- | --- | --- | --- |
| TC-701 | Extra steps? | Flow should feel short and direct | Pending |  |
| TC-702 | Unclear buttons? | Every button has a clear purpose | Pending |  |
| TC-703 | Slow loading? | Loading state is visible and reassuring | Pending |  |
| TC-704 | Too many clicks? | Core actions are reachable fast | Pending |  |
| TC-705 | Empty screens? | Empty state tells user what to do next | Pending |  |

## Release Gate

- All happy path items are PASS
- No critical or high bugs remain open
- Backend tests pass
- Frontend build passes
- Docs updated
- Manual QA signed off

## Notes

- If a step fails, create an issue instead of patching silently.
- Keep this file updated during every RC run.
