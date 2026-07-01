# Configuration and Environments

## Purpose

Xác định biến môi trường và môi trường chạy cho Phase 4 và Phase 5.

## Environments

| Environment | Purpose |
| --- | --- |
| Development | local development and debugging |
| Staging | integration testing and demo |
| Production | real user traffic |

## Required configuration

- database URL
- redis URL
- JWT secret
- refresh token secret
- OpenAI API key
- app base URL
- frontend API base URL
- log level
- environment name

## Rules

- secrets must not be committed
- dev config should be safe for local use
- staging should mirror production behavior as closely as practical

## Runtime configuration

- feature flags can be used later
- keep environment-specific behavior small and explicit

