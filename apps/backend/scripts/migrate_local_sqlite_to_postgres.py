from __future__ import annotations

import json
import sqlite3
import sys
from datetime import UTC, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url


BACKEND_ROOT = Path(__file__).resolve().parents[1]
WORKSPACE_ROOT = Path(__file__).resolve().parents[4]
SOURCE_DB = WORKSPACE_ROOT / "ai_planner_v2.db"
LOCAL_TIME_ZONE = ZoneInfo("Asia/Ho_Chi_Minh")

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from src.core.config import get_settings  # noqa: E402


TABLE_ORDER = [
    "users",
    "tasks",
    "activity_events",
]

DATETIME_COLUMNS = {
    "created_at",
    "updated_at",
    "deleted_at",
    "completed_at",
    "occurred_at",
    "expires_at",
    "revoked_at",
}

JSON_COLUMNS = {
    "tasks": {"tags"},
    "activity_events": {"payload"},
    "user_preferences": set(),
    "user_schedule_preferences": {"day_offs", "focus_hours"},
    "context_snapshots": {"context_payload"},
    "ai_suggestions": set(),
    "day_summaries": {"summary_payload"},
    "feedback": set(),
}


def parse_value(column: str, value: object) -> object:
    if value is None:
        return None

    if column in DATETIME_COLUMNS:
        parsed = datetime.fromisoformat(str(value))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=LOCAL_TIME_ZONE)
        return parsed.astimezone(UTC)

    return value


def load_rows(db: sqlite3.Connection, table: str) -> list[dict[str, object]]:
    cursor = db.execute(f'SELECT * FROM "{table}"')
    columns = [desc[0] for desc in cursor.description or []]
    rows: list[dict[str, object]] = []
    for raw_row in cursor.fetchall():
        row = {}
        for column, value in zip(columns, raw_row, strict=False):
            parsed_value = parse_value(column, value)
            if table in JSON_COLUMNS and column in JSON_COLUMNS[table] and parsed_value is not None:
                parsed_value = json.dumps(json.loads(str(parsed_value)))
            row[column] = parsed_value
        rows.append(row)
    return rows


def main() -> int:
    if not SOURCE_DB.exists():
        print(f"Source SQLite database not found: {SOURCE_DB}")
        return 1

    settings = get_settings()
    database_url = settings.database_url or settings.direct_url
    if not database_url:
        print("DATABASE_URL or DIRECT_URL is not configured.")
        return 1

    url = make_url(database_url)
    if url.drivername == "postgresql":
        url = url.set(drivername="postgresql+psycopg")
    if "pgbouncer" in url.query:
        url = url.set(query={key: value for key, value in url.query.items() if key != "pgbouncer"})
    engine = create_engine(url.render_as_string(hide_password=False), future=True)
    source = sqlite3.connect(SOURCE_DB)
    source.row_factory = sqlite3.Row

    user_id_map: dict[str, str] = {}
    task_id_map: dict[str, str] = {}
    inserted_counts: dict[str, int] = {table: 0 for table in TABLE_ORDER}
    skipped_counts: dict[str, int] = {table: 0 for table in TABLE_ORDER}

    try:
        with engine.begin() as conn:
            for table in TABLE_ORDER:
                rows = load_rows(source, table)
                if not rows:
                    continue

                for row in rows:
                    if table == "users":
                        existing_id = conn.execute(
                            text('SELECT id FROM users WHERE email = :email'),
                            {"email": row["email"]},
                        ).scalar_one_or_none()
                        if existing_id:
                            user_id_map[str(row["id"])] = str(existing_id)
                            skipped_counts[table] += 1
                            continue

                        conn.execute(
                            text(
                                """
                                INSERT INTO users (
                                    id, email, password_hash, name, timezone, role,
                                    created_at, updated_at, deleted_at
                                ) VALUES (
                                    :id, :email, :password_hash, :name, :timezone, :role,
                                    :created_at, :updated_at, :deleted_at
                                )
                                """
                            ),
                            row,
                        )
                        user_id_map[str(row["id"])] = str(row["id"])
                        inserted_counts[table] += 1
                        continue

                    if table == "tasks":
                        source_user_id = str(row["user_id"])
                        row["user_id"] = user_id_map.get(source_user_id, source_user_id)

                        existing_id = conn.execute(
                            text("SELECT id FROM tasks WHERE id = :id"),
                            {"id": row["id"]},
                        ).scalar_one_or_none()
                        if existing_id:
                            task_id_map[str(row["id"])] = str(existing_id)
                            skipped_counts[table] += 1
                            continue

                        conn.execute(
                            text(
                                """
                                INSERT INTO tasks (
                                    id, user_id, daily_plan_id, title, description,
                                    estimated_duration, deadline, priority, status, tags,
                                    completed_at, created_at, updated_at, deleted_at
                                ) VALUES (
                                    :id, :user_id, :daily_plan_id, :title, :description,
                                    :estimated_duration, :deadline, :priority, :status, :tags,
                                    :completed_at, :created_at, :updated_at, :deleted_at
                                )
                                """
                            ),
                            row,
                        )
                        task_id_map[str(row["id"])] = str(row["id"])
                        inserted_counts[table] += 1
                        continue

                    if table == "activity_events":
                        source_user_id = row.get("user_id")
                        if source_user_id is not None:
                            row["user_id"] = user_id_map.get(str(source_user_id), str(source_user_id))

                        source_entity_id = row.get("entity_id")
                        if source_entity_id is not None:
                            row["entity_id"] = task_id_map.get(str(source_entity_id), str(source_entity_id))

                        existing_id = conn.execute(
                            text("SELECT id FROM activity_events WHERE id = :id"),
                            {"id": row["id"]},
                        ).scalar_one_or_none()
                        if existing_id:
                            skipped_counts[table] += 1
                            continue

                        conn.execute(
                            text(
                                """
                                INSERT INTO activity_events (
                                    id, user_id, event_type, entity_type, entity_id,
                                    source, payload, occurred_at
                                ) VALUES (
                                    :id, :user_id, :event_type, :entity_type, :entity_id,
                                    :source, :payload, :occurred_at
                                )
                                """
                            ),
                            row,
                        )
                        inserted_counts[table] += 1

        print("Migration completed.")
        print(f"Source database: {SOURCE_DB}")
        print(f"Target database: {database_url}")
        for table in TABLE_ORDER:
            print(f"{table}: inserted {inserted_counts[table]}, skipped {skipped_counts[table]}")
        return 0
    finally:
        source.close()


if __name__ == "__main__":
    raise SystemExit(main())
