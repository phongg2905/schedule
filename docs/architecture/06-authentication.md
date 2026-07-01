# Authentication

## Decision

Use JWT-based authentication for MVP with access token + refresh token stored in secure HTTP-only cookies.

## Why

- works well with Next.js + FastAPI
- simple enough for MVP
- easy to version and test
- compatible with API-first backend

## Token model

- access token for short-lived auth
- refresh token for session renewal

## Storage model

- access token stored in secure HTTP-only cookie
- refresh token stored in secure HTTP-only cookie
- frontend should not rely on localStorage for auth tokens

## Rules

- password must never be stored in plain text
- login required for all product data
- auth state must survive refreshes safely
- unauthorized access must fail explicitly
- refresh token should be rotatable
- logout should revoke refresh token server-side when possible

## Authorization model

- MVP starts with a single authenticated user role
- every product endpoint except auth/register, auth/login and health endpoints requires authentication
- role-based access can be introduced later without changing the token shape

## Session refresh flow

1. frontend calls protected endpoint or auth/me
2. if access token expired, backend can issue refresh flow
3. frontend requests refresh endpoint
4. backend validates refresh token
5. backend issues new access token

## Security notes

- store secrets outside repo
- rotate signing keys when needed
- keep token payload minimal
