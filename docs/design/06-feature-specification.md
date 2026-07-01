# Feature Specification

## 1. Login

### Purpose

Cho phép người dùng vào đúng dữ liệu cá nhân của mình.

### Input

- email or username
- password

### Output

- authenticated session
- redirect to Today screen

### Rule

- login xong phải vào `Today`
- không được dừng ở landing trung gian

### Edge cases

- sai mật khẩu
- hết phiên đăng nhập
- tài khoản chưa tồn tại

### Error

- hiển thị lý do rõ ràng

### Loading

- disable submit khi đang xử lý

### Retry

- cho phép nhập lại ngay

## 2. Today dashboard

### Purpose

Giúp người dùng biết trong 30 giây hôm nay cần làm gì.

### Input

- data hiện có
- task list
- lịch sử gần nhất
- state hiện tại

### Output

- daily schedule suggestion
- priority order
- quick edit actions

### Rule

- phải có trạng thái empty, loading, success, error
- luôn hiển thị lý do ngắn cho đề xuất

## 3. Task creation

### Purpose

Tạo task nhanh và nhất quán.

### Required fields

- title
- status

### Optional fields

- description
- due date
- priority
- estimated duration
- tags

### Deadline rule

- deadline không bắt buộc

### Priority rule

- priority không bắt buộc
- nếu không có, hệ thống gán `normal`

## 4. Calendar views

### Day view

- bắt buộc
- hiển thị chi tiết trong ngày

### Week view

- bắt buộc
- dùng để nhìn tổng quan phân bổ thời gian

### Month view

- không bắt buộc cho MVP
- chỉ dùng nếu không phá vỡ core flow

### Direct edit

- chỉnh sửa trực tiếp trên calendar được phép
- mọi edit phải sync lại task và schedule state

## 5. AI schedule generation

### Purpose

Tạo lịch trình khả thi cho hôm nay hoặc điều chỉnh lịch đang có.

### Input

- task list
- calendar availability
- completion history
- user feedback
- current day context
- manual changes

### When AI is called

- khi user mở Today
- khi user yêu cầu generate lại
- khi có thay đổi làm ảnh hưởng lịch
- khi hệ thống phát hiện trạng thái đủ dữ liệu để đề xuất

### Output

- suggested schedule
- explanation
- confidence or rationale label

### Generation time

- mục tiêu dưới 5 giây cho MVP local
- nếu lâu hơn phải có loading state rõ ràng

### Explanation

- giải thích ngắn gọn theo từng khối lịch
- trả lời được câu hỏi: vì sao việc này nằm ở thời điểm này

### Error

- fallback sang lịch thủ công hiện tại
- hiển thị lý do lỗi

### Retry

- cho phép generate lại
- cho phép sửa thủ công thay vì chờ AI

## 6. AI failure handling

### If AI errors

- không khóa app
- user vẫn chỉnh tay được
- hiển thị retry
- giữ lại input và trạng thái trước đó

## 7. User rejection handling

### If user dislikes AI plan

- cho phép edit trực tiếp
- cho phép regenerate
- cho phép mark as not useful
- lưu feedback để dùng cho lần sau

## 8. Progress summary

### Purpose

Lưu lại kết quả cuối ngày cho ngày tiếp theo.

### Output

- completed tasks
- postponed tasks
- schedule changes
- feedback signals

### Rule

- summary phải tạo được dữ liệu cho AI học tiếp

## 9. Coverage notes

Các câu hỏi Phase 2 được trả lời trong bộ tài liệu này:

- User: [01-user-persona.md](01-user-persona.md), [02-user-journey.md](02-user-journey.md)
- Flow: [02-user-journey.md](02-user-journey.md), [04-user-flow.md](04-user-flow.md), [07-wireframe.md](07-wireframe.md)
- Task: mục 3 của file này
- Calendar: mục 4 của file này
- AI: mục 5, 6 và 7 của file này
