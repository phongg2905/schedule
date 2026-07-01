# AI Context

## Purpose

Xác định AI sẽ nhận dữ liệu nào để đề xuất lịch trình phù hợp và giải thích được.

## Context goals

- hiểu user hiện tại
- hiểu ngày hiện tại
- hiểu trạng thái task và lịch
- hiểu những gì đã xảy ra gần đây
- hiểu phản hồi trước đó của user

## Context layers

### Stable context

- user profile
- preferences
- working pattern
- timezone

### Short-term context

- tasks today
- schedule today
- completed items
- recent changes
- recent feedback

### Behavioral context

- recurring reschedules
- completion patterns
- rejection patterns
- preferred time windows

### Session context

- current date
- current time
- current availability
- request source

## Context windows

### Today open window

Khi user mở app để xem kế hoạch hôm nay, AI chỉ cần:

- current day tasks
- current schedule
- session context
- behavioral summary của 7 ngày gần nhất
- feedback liên quan gần đây nhất

### Daily generation window

Khi AI tạo lịch cho ngày hiện tại, AI cần:

- current day tasks
- schedule today
- availability window
- recent changes trong 24 giờ gần nhất
- behavioral summary của 14 ngày gần nhất
- feedback liên quan trong 30 ngày gần nhất
- user profile và preferences

### Adjustment window

Khi có thay đổi trong ngày, AI cần:

- current schedule snapshot
- task affected
- events kể từ đầu ngày
- availability bị thay đổi
- những task còn lại trong ngày

### Summary window

Khi tổng kết cuối ngày, hệ thống cần:

- all day events
- completed tasks
- postponed tasks
- accepted/rejected suggestions
- manual edits

## What AI should not receive by default

- raw unrelated history
- full event stream without windowing
- sensitive data not needed for planning
- UI-only metadata

## Context assembly rules

- build from current user action and recent events
- window history by relevance, not by volume
- include summary if event history is too long
- cache snapshot when generating suggestions
- prefer event aggregates over raw event lists when possible
- include only events that can influence the current decision
- trim history outside the active window unless explicitly needed for audit or debugging

## Context snapshot

Mỗi lần generate AI nên tạo một `ContextSnapshot` để:

- truy vết đề xuất nào dùng dữ liệu nào
- debug khi AI trả lời sai
- phân tích chất lượng prompt trong tương lai
- lưu window type đã dùng
- lưu thời điểm chụp context
- lưu nguồn dữ liệu chính đã được đưa vào prompt

## AI decision boundaries

- AI chỉ đề xuất, không ép buộc
- AI phải có thể giải thích bằng dữ liệu đầu vào
- nếu context thiếu, hệ thống phải fallback thay vì đoán bừa
