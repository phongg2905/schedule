# Product Foundation

## Mục đích

Tài liệu này là điểm chốt cho Phase 1. Nó gom các quyết định nền tảng để các phase sau không phải suy đoán lại định vị sản phẩm.

## Product summary

AI Planner là một AI Companion hỗ trợ người dùng:

- hiểu bối cảnh trước khi lập kế hoạch
- đề xuất lịch trình phù hợp
- giải thích lý do cho từng đề xuất
- học từ phản hồi và lịch sử sử dụng
- giảm gánh nặng ra quyết định mỗi ngày

## Người dùng mục tiêu

- học sinh, sinh viên
- người đi làm bận rộn
- người cần hỗ trợ lập kế hoạch và điều chỉnh lịch linh hoạt

## Vấn đề cốt lõi

Người dùng không thiếu công cụ ghi chú hay lịch. Họ thiếu một hệ thống giúp:

- quyết định nên làm gì tiếp theo
- ưu tiên việc nào trước
- điều chỉnh kế hoạch khi hoàn cảnh thay đổi

## Giá trị cốt lõi

- Understand Before Planning
- Recommend, Never Force
- Explain Every Suggestion
- Learn Continuously
- User Always Has Final Decision

## MVP guardrails

- Chỉ xây những gì phục vụ lập kế hoạch và điều chỉnh lịch
- Không xây chatbot đa năng
- Không xây social features
- Không thêm feature nếu chưa chứng minh được giá trị
- AI chỉ được gọi khi thật sự cần

## Data strategy

Hệ thống phải lưu được dữ liệu có cấu trúc cho các bước sau:

- task and schedule history
- behavior signals
- AI suggestions
- user feedback
- completion events
- change history

## Tiêu chí Phase 1 hoàn tất

- định vị sản phẩm rõ ràng
- phạm vi MVP được khóa
- roadmap có thể dùng làm baseline
- tài liệu đủ sạch để bắt đầu UX, architecture và database
