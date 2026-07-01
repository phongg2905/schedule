# Security

## Purpose

Xác định các điểm bảo vệ tối thiểu cần có cho AI Planner ngay từ đầu.

## Security baseline

- password hashing
- input validation
- authentication protection
- rate limiting
- API key management
- prompt injection awareness
- CORS policy
- security headers
- dependency scanning

## Password handling

- hash passwords with a strong one-way algorithm
- never store plain text passwords
- never log secrets

## API protection

- validate all incoming payloads
- reject invalid or oversized input
- rate limit AI endpoints more aggressively than normal endpoints
- protect against SQL injection through ORM usage and parameterized queries
- set strict CORS for frontend origin only
- add CSRF protection if cookie-based auth requires it

## Password hashing

- use a strong adaptive hashing algorithm
- store only hashed passwords
- never log password values

## AI-specific risks

- prompt injection
- data leakage through context
- malformed response injection
- prompt injection via user task notes or descriptions

## File upload security

- if uploads are added later, validate type and size
- store uploads outside executable paths
- scan uploaded content before further processing

## Mitigation rules

- sanitize user-provided text before prompt assembly
- send only relevant context
- validate structured AI output before persistence
- keep AI keys server-side only
- hide secrets from logs
- keep dependency updates under review

## Security headers

- content security policy
- x-frame-options
- x-content-type-options
- referrer policy
- permissions policy
