from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Protocol
from urllib import error, request


@dataclass
class ScheduleItemResult:
    task_id: str
    label: str
    start_time: str
    end_time: str
    reason: str


@dataclass
class DailyPlanResult:
    status: str  # "ok" | "partial" | "day_off" | "needs_review"
    ordered_task_ids: list[str]
    schedule_items: list[ScheduleItemResult]
    overflow_task_ids: list[str] = field(default_factory=list)
    explanation: str = ""
    confidence: float = 0.0
    highlights: list[str] = field(default_factory=list)


@dataclass
class AdjustmentResult:
    suggestion: str
    explanation: str


class DailyPlanAIProvider(Protocol):
    def generate_daily_plan(self, context: dict) -> DailyPlanResult:
        ...

    def explain_plan(self, context: dict) -> str:
        ...

    def adjust_plan(self, context: dict) -> AdjustmentResult:
        ...


_SYSTEM_PROMPT = """Bạn là AI Planner, nhiệm vụ của bạn là tạo lịch làm việc trong ngày cho người dùng dựa trên dữ liệu đầu vào được cung cấp.

Mục tiêu:
- Tạo một lịch khả thi, thực tế, bám sát thói quen và ưu tiên của người dùng.
- Chỉ đề xuất, không tự ý thay đổi dữ liệu cuối cùng.
- Nếu dữ liệu thiếu hoặc có xung đột, ưu tiên phương án an toàn, hợp lý, và dễ chỉnh sửa.

Nguyên tắc:
1. Tôn trọng ràng buộc cứng:
   - giờ làm việc
   - giờ nghỉ trưa
   - ngày nghỉ
   - timezone
   - xung đột thời gian
   - giới hạn thời lượng trong ngày
2. Ưu tiên theo:
   - deadline gần hơn
   - mức độ ưu tiên cao hơn
   - task ngắn hơn nếu cần tối ưu slot trống
   - thói quen và phản hồi gần đây của người dùng
3. Chỉ dùng dữ liệu liên quan trực tiếp đến ngày hiện tại và lịch gần đây.
4. Không dùng toàn bộ lịch sử thô nếu không cần.
5. Không bịa dữ liệu.
6. Không trả lời lan man. Kết quả phải rõ ràng, có cấu trúc, dễ parse.
7. Nếu không thể xếp hết task, hãy nêu rõ task nào bị overflow và vì sao.
8. Nếu người dùng có day-off, không tạo lịch làm việc, chỉ trả về trạng thái nghỉ.
9. Output phải là JSON hợp lệ, không thêm văn bản ngoài JSON.

Dữ liệu đầu vào có thể gồm:
- user profile
- timezone
- work_start_time
- work_end_time
- lunch_start_time
- lunch_end_time
- day_offs
- focus_hours
- tasks của ngày hôm nay
- schedule hiện tại
- completed / skipped / deferred gần đây
- feedback và preference gần đây
- current date and time
- trigger_source
- context_window_type

Nhiệm vụ của bạn:
- Sắp xếp task theo thứ tự hợp lý trong ngày.
- Phân bổ task vào các khung giờ phù hợp.
- Giữ lịch thực tế, không nhồi quá mức.
- Tạo giải thích ngắn gọn cho kế hoạch.
- Nếu có thay đổi so với lịch cũ, hãy đề xuất điều chỉnh tối thiểu cần thiết.
- Nếu không đủ chỗ, đánh dấu task bị overflow.

Định dạng output JSON:
{{
  "status": "ok" | "partial" | "day_off" | "needs_review",
  "ordered_task_ids": ["task_id_1", "task_id_2"],
  "schedule_items": [
    {{
      "task_id": "task_id_1",
      "label": "Task title",
      "start_time": "YYYY-MM-DDTHH:MM:SS",
      "end_time": "YYYY-MM-DDTHH:MM:SS",
      "reason": "short explanation"
    }}
  ],
  "overflow_task_ids": ["task_id_3"],
  "explanation": "A concise explanation of why this plan is ordered this way.",
  "confidence": 0.0,
  "highlights": [
    "Short note 1",
    "Short note 2"
  ]
}}

Ràng buộc khi tạo JSON:
- Chỉ dùng task_id có trong input.
- Không tạo field lạ.
- Không để JSON lỗi.
- Không đưa markdown, không đưa code fence.
- Explanation phải ngắn, thực tế, dễ hiểu.
- Confidence là số từ 0 đến 1.

Nếu dữ liệu đầu vào không đủ để ra quyết định chắc chắn:
- vẫn tạo phương án tốt nhất có thể
- giảm confidence
- ghi rõ trong explanation phần còn thiếu là gì
- không bịa thêm task hoặc thời gian.
"""


class LocalDailyPlanAIProvider:
    def generate_daily_plan(self, context: dict) -> DailyPlanResult:
        tasks = context.get("tasks", [])
        preferences = context.get("preferences", {})
        plan_date = context.get("plan_date", datetime.now(UTC).strftime("%Y-%m-%d"))
        day_offs = preferences.get("day_offs", [])

        # Check day off
        from datetime import datetime as dt
        weekday = dt.fromisoformat(f"{plan_date}T00:00:00").strftime("%A")
        if weekday in day_offs:
            return DailyPlanResult(
                status="day_off",
                ordered_task_ids=[],
                schedule_items=[],
                overflow_task_ids=[task["id"] for task in tasks],
                explanation=self._localized_text(
                    context,
                    en="Today is configured as a day off. No schedule generated.",
                    vi="Hôm nay là ngày nghỉ. Không tạo lịch làm việc.",
                ),
                confidence=1.0,
                highlights=[self._localized_text(context, en="Day off", vi="Ngày nghỉ")],
            )

        work_start = preferences.get("work_start_time", "09:00")
        work_end = preferences.get("work_end_time", "17:00")
        lunch_start = preferences.get("lunch_start_time", "12:00")
        lunch_end = preferences.get("lunch_end_time", "13:00")

        ordered_task_ids = [task["id"] for task in tasks]
        schedule_items_result: list[ScheduleItemResult] = []
        overflow_task_ids: list[str] = []

        current_hour, current_min = map(int, work_start.split(":"))
        end_hour, end_min = map(int, work_end.split(":"))
        lunch_start_h, lunch_start_m = map(int, lunch_start.split(":"))
        lunch_end_h, lunch_end_m = map(int, lunch_end.split(":"))

        def to_minutes(h: int, m: int) -> int:
            return h * 60 + m

        current_mins = to_minutes(current_hour, current_min)
        work_end_mins = to_minutes(end_hour, end_min)
        lunch_start_mins = to_minutes(lunch_start_h, lunch_start_m)
        lunch_end_mins = to_minutes(lunch_end_h, lunch_end_m)

        for task in tasks:
            duration = task.get("estimated_duration", 30)
            # Check lunch overlap
            if current_mins < lunch_start_mins and current_mins + duration > lunch_start_mins:
                current_mins = lunch_end_mins
            if current_mins >= work_end_mins:
                overflow_task_ids.append(task["id"])
                continue
            if current_mins < lunch_end_mins and current_mins >= lunch_start_mins:
                current_mins = lunch_end_mins
            end_mins = current_mins + duration
            if current_mins < lunch_start_mins and end_mins > lunch_start_mins:
                current_mins = lunch_end_mins
                end_mins = current_mins + duration
            if end_mins > work_end_mins:
                overflow_task_ids.append(task["id"])
                continue

            start_str = f"{plan_date}T{current_mins // 60:02d}:{current_mins % 60:02d}:00"
            end_str = f"{plan_date}T{end_mins // 60:02d}:{end_mins % 60:02d}:00"
            schedule_items_result.append(
                ScheduleItemResult(task_id=task["id"], label=task.get("title", ""), start_time=start_str, end_time=end_str, reason="Scheduled by local fallback")
            )
            current_mins = end_mins

        total = len(tasks)
        scheduled = len(schedule_items_result)
        status = "ok" if overflow_task_ids == [] else "partial"

        return DailyPlanResult(
            status=status,
            ordered_task_ids=ordered_task_ids,
            schedule_items=schedule_items_result,
            overflow_task_ids=overflow_task_ids,
            explanation=self._localized_text(
                context,
                en=f"Local fallback: Scheduled {scheduled}/{total} tasks within {work_start}-{work_end}.",
                vi=f"Bản dự phòng: Đã xếp {scheduled}/{total} task trong khung {work_start}-{work_end}.",
            ),
            confidence=1.0,
            highlights=[
                self._localized_text(
                    context,
                    en=f"{scheduled} task(s) scheduled" if overflow_task_ids else f"All {scheduled} task(s) scheduled",
                    vi=f"Đã xếp {scheduled} task" if not overflow_task_ids else f"Đã xếp {scheduled} task, còn {len(overflow_task_ids)} task chưa xếp",
                )
            ],
        )

    def explain_plan(self, context: dict) -> str:
        plan = context["plan"]
        items = plan.get("items", [])
        if not items:
            return self._localized_text(context, en="No tasks were scheduled in the plan.", vi="Không có công việc nào được xếp trong kế hoạch.")
        first_item = items[0]
        return self._localized_text(
            context,
            en=f"{first_item['label']} appears first because the planner prioritized urgency, deadlines, and available working hours.",
            vi=f"{first_item['label']} đứng đầu vì bộ lập lịch ưu tiên độ gấp, hạn chót và khung giờ làm việc khả dụng.",
        )

    def adjust_plan(self, context: dict) -> AdjustmentResult:
        change_description = context.get("change_description", "")
        plan = context.get("plan", {})
        items = plan.get("items", [])
        if not items:
            return AdjustmentResult(
                suggestion=self._localized_text(
                    context,
                    en="No schedule changes were applied because the current plan is empty.",
                    vi="Không có thay đổi lịch nào được áp dụng vì kế hoạch hiện tại đang trống.",
                ),
                explanation=self._localized_text(
                    context,
                    en="Local fallback used because no OpenAI key is configured.",
                    vi="Bản dự phòng cục bộ được dùng vì chưa cấu hình OpenAI key.",
                ),
            )
        first_item = items[0]
        suggestion = self._localized_text(
            context,
            en=f"Move {first_item['label']} later and keep the rest of the plan unchanged.",
            vi=f"Di chuyển {first_item['label']} sang thời điểm muộn hơn và giữ nguyên phần còn lại của kế hoạch.",
        )
        if change_description:
            suggestion = self._localized_text(
                context,
                en=f"After '{change_description}', {suggestion}",
                vi=f"Sau thay đổi '{change_description}', {suggestion}",
            )
        return AdjustmentResult(
            suggestion=suggestion,
            explanation=self._localized_text(
                context,
                en="Local fallback used because no OpenAI key is configured.",
                vi="Bản dự phòng cục bộ được dùng vì chưa cấu hình OpenAI key.",
            ),
        )

    def _localized_text(self, context: dict, *, en: str, vi: str) -> str:
        return vi if str(context.get("language", "en")).lower().startswith("vi") else en


class OpenAIDailyPlanProvider:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model

    def generate_daily_plan(self, context: dict) -> DailyPlanResult:
        language = str(context.get("language", "en"))
        language_label = self._language_label(language)
        system_prompt = (
            f"Always answer in the user's preferred language: {language_label}. "
            "Only translate natural-language text. Do not translate JSON keys, enum values, field names, or schema. "
            f"{_SYSTEM_PROMPT}"
        )
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": json.dumps(context, ensure_ascii=False)},
            ],
        }
        data = self._post(payload)
        try:
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return self._parse_result(parsed)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid OpenAI response for daily plan generation") from exc

    def explain_plan(self, context: dict) -> str:
        language = str(context.get("language", "en"))
        language_label = self._language_label(language)
        payload = {
            "model": self.model,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"Always answer in the user's preferred language: {language_label}. "
                        "Only translate natural-language text. Do not translate JSON keys, enum values, field names, or schema. "
                        "Explain the plan in one concise paragraph. "
                        "Focus on why the order makes sense for the user. "
                        "Do not mention policy or hidden reasoning."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False),
                },
            ],
        }
        data = self._post(payload)
        try:
            return str(data["choices"][0]["message"]["content"]).strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid OpenAI response for plan explanation") from exc

    def adjust_plan(self, context: dict) -> AdjustmentResult:
        language = str(context.get("language", "en"))
        language_label = self._language_label(language)
        payload = {
            "model": self.model,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        f"Always answer in the user's preferred language: {language_label}. "
                        "Only translate natural-language text. Do not translate JSON keys, enum values, field names, or schema. "
                        "Suggest one concise schedule adjustment based on the user's change. "
                        "Return JSON with keys suggestion and explanation. "
                        "Keep both fields short and practical."
                    ),
                },
                {
                    "role": "user",
                    "content": json.dumps(context, ensure_ascii=False),
                },
            ],
        }
        data = self._post(payload)
        try:
            content = data["choices"][0]["message"]["content"]
            parsed = json.loads(content)
            return AdjustmentResult(suggestion=str(parsed["suggestion"]), explanation=str(parsed["explanation"]))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid OpenAI response for plan adjustment") from exc

    def _parse_result(self, parsed: dict) -> DailyPlanResult:
        schedule_items_raw = parsed.get("schedule_items", [])
        schedule_items = [
            ScheduleItemResult(
                task_id=str(item["task_id"]),
                label=str(item["label"]),
                start_time=str(item["start_time"]),
                end_time=str(item["end_time"]),
                reason=str(item.get("reason", "")),
            )
            for item in schedule_items_raw
        ]
        ordered_task_ids = [str(tid) for tid in parsed.get("ordered_task_ids", [])]
        overflow_task_ids = [str(tid) for tid in parsed.get("overflow_task_ids", [])]
        return DailyPlanResult(
            status=str(parsed.get("status", "needs_review")),
            ordered_task_ids=ordered_task_ids,
            schedule_items=schedule_items,
            overflow_task_ids=overflow_task_ids,
            explanation=str(parsed.get("explanation", "")),
            confidence=float(parsed.get("confidence", 0.0)),
            highlights=[str(h) for h in parsed.get("highlights", [])],
        )

    def _post(self, payload: dict) -> dict:
        req = request.Request(
            "https://api.openai.com/v1/chat/completions",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=20) as response:
                return json.loads(response.read().decode("utf-8"))
        except error.URLError as exc:
            raise ValueError("OpenAI request failed") from exc

    def _language_label(self, language: str) -> str:
        return "Vietnamese" if language.lower().startswith("vi") else "English"


def build_daily_plan_provider(api_key: str) -> DailyPlanAIProvider:
    if api_key.strip():
        return OpenAIDailyPlanProvider(api_key=api_key)
    return LocalDailyPlanAIProvider()
