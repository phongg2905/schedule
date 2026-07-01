# Architecture Decisions

## Purpose

Ghi lại các quyết định kiến trúc quan trọng để tránh tranh luận lại sau này.

## ADR-001

- Decision: use REST API
- Reason: simple, stable, easy to document and test for MVP

## ADR-002

- Decision: use PostgreSQL
- Reason: strong relational model, analytics support, event history support

## ADR-003

- Decision: use SQLAlchemy in backend
- Reason: explicit control over persistence layer and familiar FastAPI ecosystem fit

## ADR-004

- Decision: use JWT access token plus refresh token
- Reason: suitable for API-first web app and scalable session handling

## ADR-005

- Decision: AI only proposes, user confirms before persistence
- Reason: protects user control and reduces unsafe automation

## ADR-006

- Decision: modular monolith for MVP
- Reason: reduces operational complexity while preserving clean boundaries

## ADR-007

- Decision: structured events as source of truth
- Reason: supports behavior tracking, auditability and future AI memory

