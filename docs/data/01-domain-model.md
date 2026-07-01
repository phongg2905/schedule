# Domain Model

## Purpose

Xác định các thực thể cốt lõi của AI Planner trước khi thiết kế database.

## Core principle

Task không phải trung tâm dữ liệu duy nhất. Hệ thống phải model được hành vi, thay đổi, phản hồi và bối cảnh sử dụng.

## Core entities

### User

Người dùng của hệ thống.

### Task

Công việc người dùng tạo và theo dõi.

### Schedule

Kế hoạch theo ngày hoặc theo tuần do AI hoặc người dùng điều chỉnh.

### DailyPlan

Bản kế hoạch của một ngày cụ thể, là aggregate chính của Core Flow.

### ScheduleItem

Một khối thời gian cụ thể trong lịch.

### AI Suggestion

Đề xuất do AI tạo ra cho lịch hoặc điều chỉnh.

### Feedback

Phản hồi của người dùng đối với đề xuất hoặc kết quả.

### ActivityEvent

Sự kiện ghi lại hành động của người dùng hoặc hệ thống.

### DaySummary

Tổng kết cuối ngày để chuẩn bị cho ngày tiếp theo.

## Optional supporting entities

### Preference

Thiết lập cá nhân của người dùng.

### ContextSnapshot

Bản chụp ngữ cảnh tại thời điểm tạo đề xuất AI.

## Entity relationships

- User owns Task
- User owns Schedule
- User owns DailyPlan
- DailyPlan contains Schedule
- Schedule contains ScheduleItem
- ScheduleItem may reference Task
- AI Suggestion references DailyPlan and ContextSnapshot
- Feedback belongs to AI Suggestion or ScheduleItem
- ActivityEvent can reference any domain entity
- DaySummary aggregates ActivityEvent, Task and Schedule data

## Modeling rules

- Mọi thay đổi quan trọng phải tạo event
- Mọi đề xuất AI phải có thể truy vết về context
- Domain model phải tách dữ liệu hiện tại và dữ liệu lịch sử
- Không nhét logic presentation vào domain

## Scope note

Danh sách này là đủ cho MVP nhưng vẫn mở đường cho behavior tracking và AI memory về sau.
