from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Protocol
from urllib import error, request


@dataclass
class TaskOrderResult:
    ordered_task_ids: list[str]
    explanation: str


@dataclass
class AdjustmentResult:
    suggestion: str
    explanation: str


class DailyPlanAIProvider(Protocol):
    def rank_tasks(self, context: dict) -> TaskOrderResult: ...

    def explain_plan(self, context: dict) -> str: ...

    def adjust_plan(self, context: dict) -> AdjustmentResult: ...


class LocalDailyPlanAIProvider:
    def rank_tasks(self, context: dict) -> TaskOrderResult:
        ordered_task_ids = [task["id"] for task in context["tasks"]]
        explanation = "Local fallback used because no OpenAI key is configured."
        return TaskOrderResult(ordered_task_ids=ordered_task_ids, explanation=explanation)

    def explain_plan(self, context: dict) -> str:
        plan = context["plan"]
        items = plan.get("items", [])
        if not items:
            return "No tasks were scheduled in the plan."
        first_item = items[0]
        return f"{first_item['label']} appears first because the planner prioritized urgency, deadlines, and available working hours."

    def adjust_plan(self, context: dict) -> AdjustmentResult:
        change_description = context.get("change_description", "")
        plan = context.get("plan", {})
        items = plan.get("items", [])
        if not items:
            return AdjustmentResult(
                suggestion="No schedule changes were applied because the current plan is empty.",
                explanation="Local fallback used because no OpenAI key is configured.",
            )
        first_item = items[0]
        suggestion = f"Move {first_item['label']} later and keep the rest of the plan unchanged."
        if change_description:
            suggestion = f"After '{change_description}', {suggestion}"
        return AdjustmentResult(
            suggestion=suggestion,
            explanation="Local fallback used because no OpenAI key is configured.",
        )


class OpenAIDailyPlanProvider:
    def __init__(self, api_key: str, model: str = "gpt-4o-mini") -> None:
        self.api_key = api_key
        self.model = model

    def rank_tasks(self, context: dict) -> TaskOrderResult:
        payload = {
            "model": self.model,
            "temperature": 0.2,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You are a planning assistant. Order the tasks for a day. "
                        "Return JSON with keys ordered_task_ids and explanation. "
                        "Only use the task ids provided in the input. Keep the explanation short."
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
            ordered_task_ids = [str(task_id) for task_id in parsed["ordered_task_ids"]]
            explanation = str(parsed["explanation"])
            return TaskOrderResult(ordered_task_ids=ordered_task_ids, explanation=explanation)
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError("Invalid OpenAI response for task ranking") from exc

    def explain_plan(self, context: dict) -> str:
        payload = {
            "model": self.model,
            "temperature": 0.3,
            "messages": [
                {
                    "role": "system",
                    "content": (
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
        payload = {
            "model": self.model,
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": (
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


def build_daily_plan_provider(api_key: str) -> DailyPlanAIProvider:
    if api_key.strip():
        return OpenAIDailyPlanProvider(api_key=api_key)
    return LocalDailyPlanAIProvider()
