from __future__ import annotations

from datetime import date, datetime, timedelta
from pathlib import Path
import sys

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import sessionmaker


BACKEND_ROOT = Path(__file__).resolve().parents[1]
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.core.config import get_settings
from src.db import models  # noqa: F401
from src.db.models import ActivityEvent, AISuggestion, ContextSnapshot, DaySummary, DailyPlan, Schedule, ScheduleItem, Task, UserSchedulePreference, new_id


PLAN_START = date(2026, 7, 6)
PLAN_END = date(2026, 8, 3)
USER_EMAIL = "phamphong20092005@gmail.com"


SLOT_TEMPLATES = [
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


def main() -> int:
    settings = get_settings()
    database_url = settings.database_url or settings.direct_url
    if not database_url:
        raise RuntimeError("DATABASE_URL or DIRECT_URL is required.")

    url = make_url(database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    if "pgbouncer" in url.query:
        url = url.set(query={key: value for key, value in url.query.items() if key != "pgbouncer"})

    engine = create_engine(
        url.render_as_string(hide_password=False),
        future=True,
        connect_args={"prepare_threshold": None},
    )
    SessionLocal = sessionmaker(bind=engine, autocommit=False, autoflush=False, future=True)

    with SessionLocal() as db:
        user_id = db.execute(text("SELECT id FROM users WHERE email = :email"), {"email": USER_EMAIL}).scalar_one()

        preference = db.query(UserSchedulePreference).filter(UserSchedulePreference.user_id == user_id).one_or_none()
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

        plan_dates = []
        current_day = PLAN_START
        while current_day <= PLAN_END:
            plan_dates.append(current_day)
            current_day += timedelta(days=1)

        plan_date_strings = [day.isoformat() for day in plan_dates]

        task_ids = [
            task_id
            for (task_id,) in db.query(Task.id)
            .filter(Task.user_id == user_id, Task.deadline.in_(plan_date_strings))
            .all()
        ]
        plan_rows = (
            db.query(DailyPlan.id, DailyPlan.context_snapshot_id)
            .filter(DailyPlan.user_id == user_id, DailyPlan.plan_date.in_(plan_date_strings))
            .all()
        )
        plan_ids = [row[0] for row in plan_rows]
        snapshot_ids = [row[1] for row in plan_rows if row[1]]
        schedule_ids = [
            schedule_id
            for (schedule_id,) in db.query(Schedule.id)
            .filter(Schedule.user_id == user_id, Schedule.daily_plan_id.in_(plan_ids))
            .all()
        ]
        summary_ids = [
            summary_id
            for (summary_id,) in db.query(DaySummary.id)
            .filter(DaySummary.user_id == user_id, DaySummary.summary_date.in_(plan_date_strings))
            .all()
        ]

        db.query(ActivityEvent).filter(ActivityEvent.user_id == user_id).delete(synchronize_session=False)
        db.query(AISuggestion).filter(AISuggestion.user_id == user_id).delete(synchronize_session=False)
        if schedule_ids:
            db.query(ScheduleItem).filter(ScheduleItem.schedule_id.in_(schedule_ids)).delete(synchronize_session=False)
            db.query(Schedule).filter(Schedule.id.in_(schedule_ids)).delete(synchronize_session=False)
        if task_ids:
            db.query(Task).filter(Task.id.in_(task_ids)).delete(synchronize_session=False)
        if plan_ids:
            db.query(DailyPlan).filter(DailyPlan.id.in_(plan_ids)).delete(synchronize_session=False)
        if snapshot_ids:
            db.query(ContextSnapshot).filter(ContextSnapshot.id.in_(snapshot_ids)).delete(synchronize_session=False)
        if summary_ids:
            db.query(DaySummary).filter(DaySummary.id.in_(summary_ids)).delete(synchronize_session=False)

        for plan_day in plan_dates:
            plan_date = plan_day.isoformat()
            snapshot = ContextSnapshot(
                id=new_id(),
                user_id=user_id,
                snapshot_type="full_day_sample",
                context_payload={
                    "plan_date": plan_date,
                    "pattern": "24h-blocks",
                    "slot_count": len(SLOT_TEMPLATES),
                    "seed_source": "fix_vietnamese_sample_data.py",
                },
            )

            plan = DailyPlan(
                id=new_id(),
                user_id=user_id,
                plan_date=plan_date,
                status="confirmed",
                source="sample_full_day",
                explanation=f"Kế hoạch mẫu 24 giờ cho {plan_date} với {len(SLOT_TEMPLATES)} khung liên tục.",
                context_snapshot_id=snapshot.id,
            )
            schedule = Schedule(
                id=new_id(),
                user_id=user_id,
                daily_plan_id=plan.id,
                schedule_date=plan_date,
                schedule_type="day",
                source="sample_full_day",
            )

            db.add_all([snapshot, plan, schedule])

            day_tasks: list[Task] = []
            day_items: list[ScheduleItem] = []
            for start_clock, end_clock, label, priority in SLOT_TEMPLATES:
                task = Task(
                    id=new_id(),
                    user_id=user_id,
                    daily_plan_id=plan.id,
                    title=build_title(plan_day, start_clock, label),
                    description=build_description(plan_day, start_clock, end_clock, label),
                    estimated_duration=60,
                    deadline=plan_date,
                    start_time=start_clock,
                    task_type="scheduled",
                    priority=priority_for_slot(priority),
                    status="planned",
                    tags=["mẫu", "24h", "vi"],
                    completed_at=None,
                )
                item = ScheduleItem(
                    id=new_id(),
                    schedule_id=schedule.id,
                    task_id=task.id,
                    start_time=slot_datetime(plan_day, start_clock).isoformat(timespec="seconds"),
                    end_time=slot_datetime(plan_day, end_clock).isoformat(timespec="seconds"),
                    label=task.title,
                    status="planned",
                    source="sample_full_day",
                )
                day_tasks.append(task)
                day_items.append(item)

            db.add_all(day_tasks)
            db.add_all(day_items)

            summary_payload = {
                "summary_date": plan_date,
                "total_tasks": len(day_tasks),
                "completed_tasks": 0,
                "skipped_tasks": 0,
                "deferred_tasks": 0,
                "pending_tasks": len(day_tasks),
                "top_focus": "Giữ nhịp sinh hoạt 24 giờ đầy đủ và ổn định",
                "highlights": [
                    f"Kế hoạch mẫu cho {plan_date} có {len(day_tasks)} task phủ kín 24 giờ.",
                    "Tất cả task đã được gắn vào daily plan và schedule items.",
                ],
            }
            day_summary = DaySummary(
                id=new_id(),
                user_id=user_id,
                summary_date=plan_date,
                summary_payload=summary_payload,
            )
            db.add(day_summary)

            db.add(
                ActivityEvent(
                    id=new_id(),
                    user_id=user_id,
                    event_type="daily_plan_created",
                    entity_type="daily_plan",
                    entity_id=plan.id,
                    source="system",
                    payload={
                        "plan_date": plan_date,
                        "task_count": len(day_tasks),
                        "item_count": len(day_items),
                        "pattern": "24h-blocks",
                    },
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
                )
            )

        db.commit()
        print(f"reseeded {len(plan_dates)} days for {USER_EMAIL}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
