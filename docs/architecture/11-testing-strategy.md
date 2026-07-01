# Testing Strategy

## Purpose

Định nghĩa mức test tối thiểu để Phase 5 có thể triển khai an toàn.

## Test pyramid

- unit test
- integration test
- API test
- end-to-end test

## Chosen frameworks

- Backend unit/integration/API: pytest, pytest-asyncio, httpx
- Frontend unit/component: Vitest, Testing Library
- End-to-end: Playwright

## Backend testing

### Unit tests

- business rules
- context builder
- prompt builder
- response parser

### Integration tests

- repository with test database
- event write and read flows
- daily plan generation flow

### API tests

- auth endpoints
- tasks endpoints
- plans endpoints
- AI endpoints

### Integration test scope

- database transactions
- event writes
- AI adapter with mocked provider
- refresh token flow

## Frontend testing

### Component and feature tests

- screen rendering
- loading and error states
- form validation

### End-to-end tests

- login
- create task
- generate plan
- accept or reject AI suggestion
- complete daily flow

### UI state tests

- loading
- empty
- error
- retry

## AI testing

- structured output validation
- fallback behavior when AI output is malformed
- prompt regression checks
- mock provider tests

## Test environments

- local test runner
- isolated test database
- mocked AI provider for deterministic tests

## Test data

- use dedicated test database
- seed deterministic fixtures
- isolate event history per test case

## Minimum coverage targets

- critical business rules must be covered
- AI parsing and validation paths must be covered
- auth and permission checks must be covered
