# System Overview

## Purpose

Mô tả toàn bộ hệ thống AI Planner ở mức kỹ thuật cao trước khi viết code.

## System goal

Hệ thống phải hỗ trợ Core Flow:

User Action -> Event -> Database -> AI Context -> LLM -> AI Response -> Event

## Chosen stack

- Frontend: Next.js + TypeScript
- Backend: FastAPI + Python
- Python runtime: 3.12
- Database: PostgreSQL
- Cache / queue support: Redis
- ORM: SQLAlchemy
- Validation: Pydantic
- Auth: JWT access token + refresh token
- API style: REST
- AI provider: OpenAI API via adapter layer
- Package manager: npm for frontend, pip + venv for backend
- Deployment: Docker and Docker Compose for local MVP
- Logging: structured JSON logs
- Monitoring: request-id tracing and Sentry-compatible error tracking

## High-level components

- Next.js frontend
- FastAPI backend
- PostgreSQL database
- Redis cache / job support
- OpenAI API integration

## Main request flow

1. Browser gửi request đến Next.js UI
2. Frontend gọi FastAPI backend
3. Backend đọc dữ liệu từ PostgreSQL và Redis nếu cần
4. Backend xây dựng context từ events, daily plan và state hiện tại
5. Backend gọi OpenAI API khi có trigger hợp lệ
6. Backend parse response, ghi event và cập nhật database
7. Frontend hiển thị kết quả và cho phép user chỉnh sửa

## Actors

- end user
- frontend application
- backend application
- AI provider
- database
- background worker

## Responsibility boundaries

- frontend renders and collects intent
- backend owns validation, business rules, orchestration and persistence
- database stores current state, history and audit events
- AI provider generates suggestions only
- background worker handles delayed or non-blocking jobs

## External services

- OpenAI API
- future monitoring service if needed

## AI call points

- khi user mở Today
- khi user yêu cầu generate hoặc regenerate plan
- khi có thay đổi ảnh hưởng lịch
- khi user chấp nhận hoặc từ chối đề xuất
- khi hệ thống tổng kết cuối ngày

## Non-goals

- microservices trong MVP
- event bus phức tạp trong MVP
- overengineering cache layer
- real-time collaboration
