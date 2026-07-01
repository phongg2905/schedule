# Product Roadmap

## Phase 1 - Product Foundation

Mục tiêu của phase này là khóa định vị sản phẩm và tạo bộ tài liệu nền tảng đủ sạch để bắt đầu thiết kế UX, hệ thống và dữ liệu.

Deliverables:

- product vision
- manifesto
- goals
- MVP scope
- roadmap baseline
- changelog ban đầu

## Phase 2 - UX Blueprint

Mục tiêu của phase này là khóa Core Flow, information architecture, user flow, feature specification và wireframe đủ rõ để dev có thể build mà không phải đoán UX.

Deliverables:

- user persona
- user journey
- user story
- user flow
- information architecture
- feature specification
- wireframe

## Phase 3 - Data Architecture

Mục tiêu của phase này là chuyển UX Blueprint thành hệ dữ liệu thật: domain model, event model, data contract, AI context và database design.

Deliverables:

- domain model
- event model
- data contract
- AI context
- database design

## Phase 4 - System Architecture

Mục tiêu của phase này là khóa kiến trúc kỹ thuật tổng thể trước khi bắt đầu implementation.

Deliverables:

- system overview
- folder structure
- backend architecture
- frontend architecture
- API design
- authentication
- AI architecture
- deployment architecture
- security
- database design
- testing strategy
- observability
- error handling
- configuration and environments
- architecture decisions

## Phase 5 - Foundation Implementation

Mục tiêu của phase này là biến toàn bộ blueprint thành một codebase có thể chạy được, nhưng chưa tập trung vào việc hoàn thiện tính năng.

### Sprint 5.1 - Project Bootstrap

Mục tiêu:

- khởi tạo repo chạy được bằng Docker Compose
- xác minh frontend, backend, PostgreSQL và Redis có thể khởi động cùng nhau

Hoàn thành:

- `apps/frontend`
- `apps/backend`
- `packages/shared`
- `packages/ui`
- `packages/types`
- `infra`
- `docs`
- Docker Compose chạy được
- PostgreSQL kết nối được
- Redis kết nối được
- Next.js chạy
- FastAPI chạy
- health check hoạt động

### Sprint 5.2 - Backend Foundation

Mục tiêu:

- dựng nền backend sạch trước khi viết nghiệp vụ

Hoàn thành:

- clean architecture
- dependency injection
- SQLAlchemy
- Alembic
- logging
- config
- exception handler
- middleware
- authentication framework

### Sprint 5.3 - Frontend Foundation

Mục tiêu:

- dựng nền frontend sạch trước khi viết màn hình nghiệp vụ

Hoàn thành:

- Next.js App Router
- Tailwind
- shadcn/ui
- theme
- layout
- routing
- authentication guard
- API client
- state management nếu đã chốt

### Sprint 5.4 - Vertical Slice #1

Mục tiêu:

- chứng minh dữ liệu cốt lõi chạy được trước khi đưa AI vào

Phạm vi:

- đăng ký
- đăng nhập
- home rỗng
- tạo task
- lưu database
- hiển thị lại task

### Sprint 5.5 - Vertical Slice #2

Mục tiêu:

- thêm daily plan generation sau khi task flow ổn định

Phạm vi:

- task
- context builder
- OpenAI
- daily plan
- persist
- hiển thị daily plan

### Sprint 5.6 - Vertical Slice #3

Mục tiêu:

- thêm AI adjustment, event và feedback

Phạm vi:

- AI suggestion
- user chỉnh sửa
- persist event
- persist feedback
- persist behavior

## Phase 6 - MVP Feature Development

Mục tiêu của phase này là chuyển sang triển khai theo vertical slice, ưu tiên giá trị sử dụng được và kỷ luật chia nhỏ issue.

Nguyên tắc:

- Mỗi vertical slice phải tạo ra giá trị người dùng thật.
- Mỗi slice phải có Definition of Done rõ ràng.
- Cuối mỗi slice phải tự dùng để kiểm tra lại.
- Không bao giờ để một issue quá lớn.

Milestones:

### Milestone M0

- Authentication
- Task CRUD
- Working Schedule & Preferences

### Milestone M1

- Daily Plan Rule-based

### Milestone M2

- AI Generate
- AI Explanation

### Milestone M3

- Daily Progress
- AI Adjustment
- Insight

Vertical Slices:

### Slice 1 - Authentication

- Register
- Login
- Refresh Token
- Logout
- Protected Route
- JWT Rotation
- Validation
- Error Handling

### Slice 2 - Task CRUD

- title
- description
- estimated duration
- deadline
- priority
- status
- tags
- completed_at

### Slice 3 - Working Schedule & Preferences

- working start time
- working end time
- lunch break
- day off
- timezone
- focus hours

### Slice 4 - Daily Plan Rule-based

- sort by priority
- sort by nearest deadline
- respect duration
- respect working hours
- no OpenAI call

### Slice 5 - AI Generate Daily Plan

- task context
- prompt builder
- OpenAI
- response validator
- persist daily plan

### Slice 6 - AI Explanation

- explain schedule decisions
- answer why task ordering

### Slice 7 - Daily Progress

- complete task
- skip task
- delay task
- move task

### Slice 8 - AI Adjustment

- user adds event
- AI adjusts remaining day

### Slice 9 - Insight

- end of day summary
- behavior patterns
- progress review

## Phase 6.5 - Hardening

Objective:

- stabilize the MVP before release
- remove scaffolded behavior and API inconsistencies
- verify the end-to-end flow through manual QA

Checklist:

- Register -> Login -> Create Task -> Generate -> Complete -> Delay -> Move -> Summary
- error handling for AI/provider failures
- loading and double-click protection
- empty states for no task, no plan, and no insight
- event audit review
- performance and transaction review
- security review for auth, validation, and cookies
- documentation and changelog updates
- release criteria gate

## Version 1.0 - MVP

Mục tiêu:

- ship phiên bản đầu tiên có thể dùng hằng ngày

Phạm vi:

- backend
- frontend
- AI integration
- local deployment
- self testing

## Version 1.1

Mục tiêu:

- hoàn thiện trải nghiệm người dùng

Nội dung:

- tối ưu giao diện
- tối ưu hiệu năng
- cải thiện prompt AI
- thống kê chi tiết hơn
- sửa lỗi

## Version 2.0

Mục tiêu:

- triển khai sản phẩm lên Internet

Nội dung:

- cloud deployment
- domain
- HTTPS
- authentication hoàn chỉnh
- production database

## Version 3.0

Mục tiêu:

- cá nhân hóa mạnh hơn

Nội dung:

- AI ghi nhớ phản hồi
- phân tích hành vi
- đề xuất thông minh hơn
- insight nâng cao

## Version 4.0

Mục tiêu:

- mở rộng hệ sinh thái

Nội dung:

- Google Calendar
- Google Tasks
- đồng bộ email
- notification
- mobile app

## Version 5.0

Mục tiêu:

- thương mại hóa sản phẩm

Nội dung:

- premium
- đa người dùng
- team workspace
- dashboard quản trị
- thanh toán
- AI coach nâng cao

## Nguyên tắc phát triển

- phát triển từng bước, không nóng vội
- ưu tiên chất lượng hơn số lượng tính năng
- mỗi version phải giải quyết một vấn đề cụ thể
- dữ liệu và trải nghiệm người dùng luôn là ưu tiên hàng đầu
