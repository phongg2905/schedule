# Deployment Architecture

## Purpose

Xác định cách đóng gói và chạy hệ thống với PostgreSQL được quản lý qua Supabase.

## MVP deployment target

- Docker
- Docker Compose
- Supabase PostgreSQL as the managed database

## Environments

| Environment | Purpose |
| --- | --- |
| Development | local development and debugging |
| Staging | integration testing and demo |
| Production | real user traffic |

## Services

- web app
- API app
- Supabase PostgreSQL
- Redis

## Optional support

- Nginx if reverse proxy is needed

## Rules

- local development must be reproducible against the managed Supabase database
- environment variables must be externalized
- deployment artifacts must not contain secrets
- database migrations run before application startup in staging and production
- Alembic is the source of truth for schema changes
- rollback should revert app image first and schema second only if safe
- backups are required for production PostgreSQL

## CI/CD direction

- run tests on pull requests
- build Docker images after test pass
- deploy staging automatically when main branch is updated
- production deploy should be gated by manual approval initially

## Future-ready note

Design the stack so it can later move to cloud without changing the core app architecture.
