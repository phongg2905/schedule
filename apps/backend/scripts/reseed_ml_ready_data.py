"""
Reseed Vietnamese sample data (ML-ready, deterministic version)
==============================================================

Fixes from original fix_vietnamese_sample_data.py:
  1. Sets created_at = plan_date start (UTC) -- deterministic, tasks "exist" at snapshot time
  2. Cleans ALL existing data before reseeding (handles multi-run state)
  3. Validates: 100% tasks have daily_plan_id, all relationships are intact
  4. Same output every run (except for random UUIDs)

Usage:
    python scripts/reseed_ml_ready_data.py
"""

from __future__ import annotations

from datetime import UTC, date, datetime, timedelta
from pathlib import Path
import sys
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker

BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.core.config import get_settings
from src.db import models  # noqa: F401
from src.db.models import (
    ActivityEvent,
    AISuggestion,
    ContextSnapshot,
    DaySummary,
    DailyPlan,
    Schedule,
    ScheduleItem,
    Task,
    UserSchedulePreference,
    new_id,
)

# ---------------------------------------------------------------------------
# Constants -- deterministic
# ---------------------------------------------------------------------------

PLAN_START = date(2026, 7, 6)
PLAN_END = date(2026, 8, 3)
USER_EMAIL = "phamphong20092005@gmail.com"

# 24 block templates -- same for every day
SLOT_TEMPLATES: list[tuple[str, str, str, str]] = [
    ("00:00", "01:00", "Ngủ đêm", "low"),
    ("01:00", "02:00", "Ngủ đêm", "low"),
    ("02:00", "03:00", "Ngủ đêm", "low"),
    ("03:00", "04:00", "Ngủ đêm", "low"),
    ("04:00", "05:00", "Ngủ đêm", "low"),
    ("05:00", "06:00", "Thức dậy và giãn cơ", "low"),
    ("06:00", "07:00", "Vệ sinh cá nhân và chuẩn bị ngày mới", "normal"),
    ("07:00", "08:00", "Ăn sáng", "normal"),
    ("08:00", "09:00", "Rà soát kế hoạch trong ngày", "normal"),
    ("09:00", "10:00", "Làm việc tập trung", "high"),
    ("10:00", "11:00", "Làm việc tập trung", "high"),
    ("11:00", "12:00", "Xử lý email và tin nhắn", "high"),
    ("12:00", "13:00", "Ăn trưa", "normal"),
    ("13:00", "14:00", "Làm việc chuyên sâu", "high"),
    ("14:00", "15:00", "Làm việc chuyên sâu", "high"),
    ("15:00", "16:00", "Họp nhóm và trao đổi", "high"),
    ("16:00", "17:00", "Hoàn thiện đầu việc", "high"),
    ("17:00", "18:00", "Vận động nhẹ", "normal"),
    ("18:00", "19:00", "Ăn tối", "normal"),
    ("19:00", "20:00", "Học tập hoặc đọc tài liệu", "normal"),
    ("20:00", "21:00", "Rà soát tiến độ", "normal"),
    ("21:00", "22:00", "Thời gian cá nhân", "low"),
    ("22:00", "23:00", "Chuẩn bị đi ngủ", "low"),
    ("23:00", "24:00", "Ngủ đêm", "low"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def plan_start_utc(plan_day: date) -> datetime:
    """Return deterministic created_at: midnight UTC of plan_day."""
    return datetime(plan_day.year, plan_day.month, plan_day.day, 0, 0, 0, tzinfo=UTC)


def slot_datetime(plan_day: date, clock: str) -> datetime:
    hour, minute = map(int, clock.split(":"))
    if hour == 24:
        return datetime.combine(plan_day + timedelta(days=1), datetime.min.time())
    return datetime.combine(plan_day, datetime.min.time()).replace(hour=hour, minute=minute)


def build_title(plan_day: date, start_clock: str, label: str) -> str:
    return f"{plan_day.isoformat()} {start_clock} - {label}"


def build_description(plan_day: date, start_clock: str, end_clock: str, label: str) -> str:
    return f"Khung mẫu {plan_day.isoformat()} từ {start_clock} đến {end_clock}: {label}."


def priority_for_slot(priority: str) -> str:
    return priority


# ---------------------------------------------------------------------------
# Cleanup
# ---------------------------------------------------------------------------


def cleanup_user_data(db: Any, user_id: str) -> None:
    """Delete ALL data for this user, in dependency order."""
    # 1. Delete events and suggestions (no FKs to other user tables except user_id)
    db.execute(
        text("DELETE FROM activity_events WHERE user_id = :uid"),
        {"uid": user_id},
    )
    db.execute(
        text("DELETE FROM ai_suggestions WHERE user_id = :uid"),
        {"uid": user_id},
    )

    # 2. Delete schedule_items (FK -> schedules)
    db.execute(
        text(
            """
            DELETE FROM schedule_items WHERE schedule_id IN (
                SELECT id FROM schedules WHERE user_id = :uid
            )
            """
        ),
        {"uid": user_id},
    )

    # 3. Delete schedules (FK -> daily_plans)
    db.execute(
        text(
            """
            DELETE FROM schedules WHERE daily_plan_id IN (
                SELECT id FROM daily_plans WHERE user_id = :uid
            )
            """
        ),
        {"uid": user_id},
    )

    # 4. Delete tasks (FK -> daily_plans)
    db.execute(text("DELETE FROM tasks WHERE user_id = :uid"), {"uid": user_id})

    # 5. Delete day_summaries (FK -> users)
    db.execute(
        text("DELETE FROM day_summaries WHERE user_id = :uid"),
        {"uid": user_id},
    )

    # 6. Delete daily_plans (FK -> context_snapshots)
    db.execute(
        text("DELETE FROM daily_plans WHERE user_id = :uid"),
        {"uid": user_id},
    )

    # 7. Delete context_snapshots
    db.execute(
        text("DELETE FROM context_snapshots WHERE user_id = :uid"),
        {"uid": user_id},
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> int:
    settings = get_settings()
    database_url = settings.database_url or settings.direct_url
    if not database_url:
        raise RuntimeError("DATABASE_URL or DIRECT_URL is required.")

    url = make_url(database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    if "pgbouncer" in url.query:
        url = url.set(query={k: v for k, v in url.query.items() if k != "pgbouncer"})

    engine = create_engine(
        url.render_as_string(hide_password=False),
        future=True,
        connect_args={"prepare_threshold": None},
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    with SessionLocal() as db:
        # --- Locate user ---
        user_id = db.execute(
            text("SELECT id FROM users WHERE email = :email"),
            {"email": USER_EMAIL},
        ).scalar_one()

        print(f"Reseeding data for user: {user_id} ({USER_EMAIL})")

        # --- Ensure schedule preferences ---
        preference = db.query(UserSchedulePreference).filter(
            UserSchedulePreference.user_id == user_id
        ).one_or_none()
        if preference is None:
            preference = UserSchedulePreference(
                id=new_id(),
                user_id=user_id,
                work_start_time="00:00",
                work_end_time="23:59",
                lunch_start_time="00:00",
                lunch_end_time="00:00",
                day_offs=[],
                focus_hours=["09:00", "14:00", "20:00"],
            )
        else:
            preference.work_start_time = "00:00"
            preference.work_end_time = "23:59"
            preference.lunch_start_time = "00:00"
            preference.lunch_end_time = "00:00"
            preference.day_offs = []
            preference.focus_hours = ["09:00", "14:00", "20:00"]
        db.add(preference)

        # --- Clean existing data ---
        cleanup_user_data(db, user_id)
        db.commit()

        # --- Build date list ---
        plan_dates: list[date] = []
        current_day = PLAN_START
        while current_day <= PLAN_END:
            plan_dates.append(current_day)
            current_day += timedelta(days=1)

        print(f"  Generating {len(plan_dates)} days ({PLAN_START} to {PLAN_END})")

        total_tasks = 0
        total_items = 0

        for plan_day in plan_dates:
            plan_date_str = plan_day.isoformat()
            creation_ts = plan_start_utc(plan_day)

            # --- Context snapshot ---
            snapshot = ContextSnapshot(
                id=new_id(),
                user_id=user_id,
                snapshot_type="full_day_sample",
                context_payload={
                    "plan_date": plan_date_str,
                    "pattern": "24h-blocks",
                    "slot_count": len(SLOT_TEMPLATES),
                    "seed_source": "reseed_ml_ready_data.py",
                },
                created_at=creation_ts,
                updated_at=creation_ts,
            )

            # --- DailyPlan ---
            plan = DailyPlan(
                id=new_id(),
                user_id=user_id,
                plan_date=plan_date_str,
                status="confirmed",
                source="sample_full_day",
                explanation=(
                    f"Kế hoạch mẫu 24 giờ cho {plan_date_str} "
                    f"với {len(SLOT_TEMPLATES)} khung liên tục."
                ),
                context_snapshot_id=snapshot.id,
                created_at=creation_ts,
                updated_at=creation_ts,
            )

            # --- Schedule ---
            schedule = Schedule(
                id=new_id(),
                user_id=user_id,
                daily_plan_id=plan.id,
                schedule_date=plan_date_str,
                schedule_type="day",
                source="sample_full_day",
                created_at=creation_ts,
                updated_at=creation_ts,
            )

            db.add_all([snapshot, plan, schedule])

            # --- Tasks + ScheduleItems ---
            day_tasks: list[Task] = []
            day_items: list[ScheduleItem] = []
            for start_clock, end_clock, label, priority in SLOT_TEMPLATES:
                task = Task(
                    id=new_id(),
                    user_id=user_id,
                    daily_plan_id=plan.id,  # 100% linkage ✓
                    title=build_title(plan_day, start_clock, label),
                    description=build_description(
                        plan_day, start_clock, end_clock, label
                    ),
                    estimated_duration=60,
                    deadline=plan_date_str,
                    start_time=start_clock,
                    task_type="scheduled",
                    priority=priority_for_slot(priority),
                    status="planned",
                    tags=["mẫu", "24h", "vi"],
                    completed_at=None,
                    created_at=creation_ts,
                    updated_at=creation_ts,
                )
                item = ScheduleItem(
                    id=new_id(),
                    schedule_id=schedule.id,
                    task_id=task.id,
                    start_time=slot_datetime(plan_day, start_clock).isoformat(
                        timespec="seconds"
                    ),
                    end_time=slot_datetime(plan_day, end_clock).isoformat(
                        timespec="seconds"
                    ),
                    label=task.title,
                    status="planned",
                    source="sample_full_day",
                    created_at=creation_ts,
                    updated_at=creation_ts,
                )
                day_tasks.append(task)
                day_items.append(item)

            db.add_all(day_tasks)
            db.add_all(day_items)
            total_tasks += len(day_tasks)
            total_items += len(day_items)

            # --- DaySummary ---
            summary_payload = {
                "summary_date": plan_date_str,
                "total_tasks": len(day_tasks),
                "completed_tasks": 0,
                "skipped_tasks": 0,
                "deferred_tasks": 0,
                "pending_tasks": len(day_tasks),
                "top_focus": "Giữ nhịp sinh hoạt 24 giờ đầy đủ và ổn định",
                "highlights": [
                    f"Kế hoạch mẫu cho {plan_date_str} có {len(day_tasks)} task phủ kín 24 giờ.",
                    "Tất cả task đã được gắn vào daily plan và schedule items.",
                ],
            }
            day_summary = DaySummary(
                id=new_id(),
                user_id=user_id,
                summary_date=plan_date_str,
                summary_payload=summary_payload,
                created_at=creation_ts,
                updated_at=creation_ts,
            )
            db.add(day_summary)

            # --- Activity Events (deterministic timestamps) ---
            db.add(
                ActivityEvent(
                    id=new_id(),
                    user_id=user_id,
                    event_type="daily_plan_created",
                    entity_type="daily_plan",
                    entity_id=plan.id,
                    source="system",
                    payload={
                        "plan_date": plan_date_str,
                        "task_count": len(day_tasks),
                        "item_count": len(day_items),
                        "pattern": "24h-blocks",
                    },
                    occurred_at=creation_ts,
                )
            )
            db.add(
                ActivityEvent(
                    id=new_id(),
                    user_id=user_id,
                    event_type="day_summary_generated",
                    entity_type="day_summary",
                    entity_id=day_summary.id,
                    source="system",
                    payload=summary_payload,
                    occurred_at=creation_ts,
                )
            )

        db.commit()

        # ------------------------------------------------------------------
        # Post-seed validation
        # ------------------------------------------------------------------
        print(f"\n=== VALIDATION ===")

        # Count all tasks
        task_count = db.execute(
            text("SELECT COUNT(*) FROM tasks WHERE user_id = :uid"),
            {"uid": user_id},
        ).scalar()
        print(f"  Tasks created: {task_count}")

        # Count tasks with daily_plan_id
        tasks_with_plan = db.execute(
            text(
                "SELECT COUNT(*) FROM tasks "
                "WHERE user_id = :uid AND daily_plan_id IS NOT NULL"
            ),
            {"uid": user_id},
        ).scalar()
        plan_pct = tasks_with_plan / task_count * 100 if task_count else 0
        print(f"  Tasks with daily_plan_id: {tasks_with_plan} ({plan_pct:.1f}%)")
        if tasks_with_plan < task_count:
            print("  WARNING: Some tasks missing daily_plan_id - NOT EXPECTED")
        else:
            print("  All tasks have daily_plan_id (100%)")

        # Count daily plans
        plan_count = db.execute(
            text("SELECT COUNT(*) FROM daily_plans WHERE user_id = :uid"),
            {"uid": user_id},
        ).scalar()
        expected_plans = len(plan_dates)
        print(f"  Daily plans: {plan_count} (expected: {expected_plans})")
        if plan_count != expected_plans:
            print(f"  WARNING: Plan count mismatch!")

        # Count schedule_items
        item_count = db.execute(
            text("SELECT COUNT(*) FROM schedule_items si "
                 "JOIN schedules s ON s.id = si.schedule_id "
                 "WHERE s.user_id = :uid"),
            {"uid": user_id},
        ).scalar()
        print(f"  Schedule items: {item_count}")
        if item_count != task_count:
            print(f"  WARNING: Item count != task count!")

        # Check created_at consistency
        sample_tasks = db.execute(
            text(
                "SELECT deadline, created_at FROM tasks "
                "WHERE user_id = :uid ORDER BY deadline LIMIT 3"
            ),
            {"uid": user_id},
        ).fetchall()
        print(f"\n  Sample created_at mapping:")
        for t in sample_tasks:
            print(f"    deadline={t[0]}  created_at={t[1]}")

        # Check: earliest and latest created_at
        extent = db.execute(
            text(
                "SELECT MIN(created_at), MAX(created_at) FROM tasks "
                "WHERE user_id = :uid"
            ),
            {"uid": user_id},
        ).fetchone()
        print(f"  created_at range: {extent[0]} -> {extent[1]}")

        # Summary
        print(f"\nReseed complete: {total_tasks} tasks across {len(plan_dates)} days")
        print(f"   Total schedule items: {total_items}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
