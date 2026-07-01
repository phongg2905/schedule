# Event Model

## Purpose

Event là source of truth ở tầng sản phẩm. Mọi hành động quan trọng của user và AI phải được lưu dưới dạng event.

## Event design principles

- append-first
- immutable after write
- human-readable type names
- every event has actor, timestamp, entity reference and source
- events must support analytics, audit log and AI learning

## Taxonomy rules

- Event name uses `snake_case`
- Event name describes what happened, not where it happened
- Event name must be stable and past-tense in meaning
- One event represents one meaningful business action
- UI clicks without business meaning are not events
- Every event belongs to exactly one category: `user`, `ai`, or `system`

## Event categories

### User action events

User chủ động tạo ra thay đổi trong dữ liệu.

### AI decision events

AI tạo, sửa, hoặc bị người dùng chấp nhận/từ chối trên một đề xuất cụ thể.

### System lifecycle events

Hệ thống ghi nhận mốc vòng đời, tổng kết, hoặc snapshot.

## Common event fields

- event_id
- event_type
- occurred_at
- user_id
- entity_type
- entity_id
- source
- payload
- metadata

## Event types

### User events

- user_signed_in
- user_profile_updated
- task_created
- task_updated
- task_deleted
- task_completed
- task_rescheduled
- schedule_item_created
- schedule_item_updated
- schedule_item_deleted
- feedback_submitted
- daily_plan_created
- daily_plan_updated
- daily_plan_completed

### AI events

- ai_schedule_requested
- ai_schedule_generated
- ai_schedule_generation_failed
- ai_suggestion_accepted
- ai_suggestion_rejected
- ai_suggestion_edited
- ai_day_summary_generated

### System events

- day_started
- day_ended
- context_snapshot_created
- analytics_snapshot_created
- event_stream_compacted

## Required MVP events

Đây là nhóm event tối thiểu phải có để Core Flow hoạt động và đo được hành vi:

- user_signed_in
- task_created
- task_updated
- task_deleted
- task_completed
- task_rescheduled
- schedule_item_created
- schedule_item_updated
- schedule_item_deleted
- daily_plan_created
- daily_plan_updated
- daily_plan_completed
- ai_schedule_requested
- ai_schedule_generated
- ai_schedule_generation_failed
- ai_suggestion_accepted
- ai_suggestion_rejected
- ai_suggestion_edited
- feedback_submitted
- day_started
- day_ended
- context_snapshot_created

## Example payloads

### task_created

```json
{
  "title": "Học React",
  "priority": "normal",
  "due_date": null,
  "source": "manual"
}
```

### task_rescheduled

```json
{
  "from": "2026-06-30T09:00:00+07:00",
  "to": "2026-06-30T11:00:00+07:00",
  "reason": "conflict"
}
```

### ai_schedule_generated

```json
{
  "mode": "daily_plan",
  "generation_time_ms": 3200,
  "context_snapshot_id": "ctx_01",
  "daily_plan_id": "plan_01"
}
```

### ai_suggestion_rejected

```json
{
  "reason": "too_dense",
  "feedback_note": "Lịch sáng quá kín"
}
```

## Event storage rules

- event phải ghi ngay khi action xảy ra
- event không được overwrite
- event payload phải đủ để tái dựng lịch sử hành vi
- event type phải ổn định để analytics không vỡ
- event phải có `source` rõ ràng: `manual`, `ai`, hoặc `system`
- event cần đủ dữ liệu để phân biệt `accepted`, `rejected`, `edited`
- event không nên chứa dữ liệu UI-only như animation state hay component state

## Analytics value

Event model cho phép:

- đo user behavior
- đo acceptance rate của AI
- hiểu task drift và reschedule patterns
- xây AI memory về sau

## Naming guidance

- `task_created`: người dùng tạo task mới
- `task_rescheduled`: thời gian task thay đổi
- `daily_plan_created`: kế hoạch ngày được tạo lần đầu
- `daily_plan_updated`: kế hoạch ngày bị chỉnh lại
- `ai_schedule_requested`: hệ thống hoặc user yêu cầu AI tạo lịch
- `ai_schedule_generated`: AI trả về một lịch hợp lệ
- `ai_suggestion_rejected`: user không đồng ý đề xuất AI

## Daily plan semantics

- `daily_plan` là aggregate cấp ngày
- `schedule` là cấu trúc phân bổ thời gian bên trong daily plan
- mọi event cấp lịch trong MVP nên gắn được về một `daily_plan_id`
