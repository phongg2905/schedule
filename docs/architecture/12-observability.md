# Observability

## Purpose

Định nghĩa cách theo dõi hệ thống trong MVP mà không overengineering.

## Logging

- structured JSON logs
- include request_id
- include user_id when available
- include operation name
- include outcome and duration
- keep logs free of secrets and sensitive prompt content

## Request tracing

- generate a request id per incoming request
- propagate it through backend calls
- include it in logs and error responses

## Metrics

- request latency
- error rate
- AI call count
- AI token usage
- daily plan generation success rate
- task completion rate
- AI acceptance rate
- retry rate

## Health checks

- liveness endpoint
- readiness endpoint

## Error tracking

- capture backend exceptions
- capture AI provider failures
- avoid logging sensitive payloads

## Tooling direction

- JSON logs are the default observability source for MVP
- Sentry-compatible error tracking can be added for exception aggregation
- metrics should be exportable later without rewriting business code

## Monitoring approach

- start with log-based monitoring and simple health endpoints
- add external alerting later if production needs it
