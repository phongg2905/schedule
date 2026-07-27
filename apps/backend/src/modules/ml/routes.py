"""
Phase 6: ML Monitoring API Routes
===================================

Provides monitoring endpoints for ML prediction quality, outcome reconciliation,
and drift detection by querying ``MLPredictionLog``.

Usage:
    GET /api/v1/ml/monitoring  — returns prediction stats for the current user
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi import APIRouter, Depends
from sqlalchemy import text as sqltext
from sqlalchemy.orm import Session

from src.dependencies import db_session, get_user_from_access_token
from src.modules.ml.schemas import (
    BandDistribution,
    DriftSignal,
    MLMonitoringResponse,
    ModelVersionSummary,
    OutcomeBreakdown,
    ScoreTrend,
)

router = APIRouter()

_SEVEN_DAYS = timedelta(days=7)


@router.get("/monitoring", response_model=MLMonitoringResponse)
def get_ml_monitoring(
    user=Depends(get_user_from_access_token),
    db: Session = Depends(db_session),
) -> MLMonitoringResponse:
    """Return ML prediction stats for the authenticated user.

    Includes confidence band distribution, outcome breakdown, score trends,
    and drift signals.
    """
    now = datetime.now(UTC)
    since_7d = now - _SEVEN_DAYS
    uid = user.id

    # --- Totals ---
    total = _scalar(db, "SELECT COUNT(*) FROM ml_prediction_logs WHERE user_id = :uid", {"uid": uid})
    recent = _scalar(
        db, "SELECT COUNT(*) FROM ml_prediction_logs WHERE user_id = :uid AND created_at >= :since",
        {"uid": uid, "since": since_7d},
    )

    if total == 0:
        return MLMonitoringResponse(total_predictions=0, recent_7d_predictions=0,
                                    confidence_distribution=[], outcome_breakdown=[],
                                    model_versions=[])

    # --- Confidence band distribution ---
    band_rows = db.execute(sqltext("""
        SELECT confidence_band, COUNT(*) AS cnt, ROUND(AVG(prediction_score), 4) AS avg_score
        FROM ml_prediction_logs
        WHERE user_id = :uid
        GROUP BY confidence_band
        ORDER BY MIN(prediction_score) DESC
    """), {"uid": uid}).fetchall()

    confidence_distribution = [
        BandDistribution(band=row[0], count=row[1],
                         percentage=round(row[1] / total * 100, 1),
                         avg_score=row[2] if row[2] is not None else 0.0)
        for row in band_rows
    ]

    # --- Outcome breakdown ---
    outcome_rows = db.execute(sqltext("""
        SELECT COALESCE(outcome, 'unset') AS outcome, COUNT(*) AS cnt
        FROM ml_prediction_logs
        WHERE user_id = :uid
        GROUP BY outcome
        ORDER BY cnt DESC
    """), {"uid": uid}).fetchall()

    outcome_breakdown = [
        OutcomeBreakdown(outcome=row[0], count=row[1],
                         percentage=round(row[1] / total * 100, 1))
        for row in outcome_rows
    ]

    # --- High-confidence completion rate ---
    high_total = _scalar(
        db, "SELECT COUNT(*) FROM ml_prediction_logs WHERE user_id = :uid AND confidence_band = 'high'",
        {"uid": uid},
    )
    high_completed = _scalar(
        db, "SELECT COUNT(*) FROM ml_prediction_logs WHERE user_id = :uid AND confidence_band = 'high' AND outcome = 'completed'",
        {"uid": uid},
    )
    completion_rate = round(high_completed / high_total * 100, 1) if high_total > 0 else None

    # --- Score trend ---
    recent_row = db.execute(sqltext("""
        SELECT ROUND(AVG(prediction_score), 4), ROUND(MIN(prediction_score), 4),
               ROUND(MAX(prediction_score), 4), COUNT(*)
        FROM ml_prediction_logs
        WHERE user_id = :uid AND created_at >= :since
    """), {"uid": uid, "since": since_7d}).fetchone()

    all_row = db.execute(sqltext("""
        SELECT ROUND(AVG(prediction_score), 4), ROUND(MIN(prediction_score), 4),
               ROUND(MAX(prediction_score), 4), COUNT(*)
        FROM ml_prediction_logs
        WHERE user_id = :uid
    """), {"uid": uid}).fetchone()

    score_trend_recent = None
    score_trend_all = None
    drift = None

    if recent_row and recent_row[3] > 0:
        score_trend_recent = ScoreTrend(
            period="7d", avg_score=recent_row[0] or 0.0,
            min_score=recent_row[1] or 0.0, max_score=recent_row[2] or 0.0,
            count=recent_row[3],
        )

    if all_row and all_row[3] > 0:
        score_trend_all = ScoreTrend(
            period="all", avg_score=all_row[0] or 0.0,
            min_score=all_row[1] or 0.0, max_score=all_row[2] or 0.0,
            count=all_row[3],
        )

    if score_trend_recent and score_trend_all and score_trend_all.avg_score > 0:
        drift_pct = round((score_trend_recent.avg_score - score_trend_all.avg_score)
                          / score_trend_all.avg_score * 100, 2)
        drift = DriftSignal(
            recent_avg=score_trend_recent.avg_score,
            all_time_avg=score_trend_all.avg_score,
            drift_pct=drift_pct,
            alert=abs(drift_pct) > 10,
        )

    # --- Model versions ---
    version_rows = db.execute(sqltext("""
        SELECT model_version, model_type, COUNT(*) AS cnt
        FROM ml_prediction_logs
        WHERE user_id = :uid
        GROUP BY model_version, model_type
        ORDER BY cnt DESC
    """), {"uid": uid}).fetchall()

    model_versions = [
        ModelVersionSummary(
            model_version=row[0], model_type=row[1],
            count=row[2], percentage=round(row[2] / total * 100, 1),
        )
        for row in version_rows
    ]

    return MLMonitoringResponse(
        total_predictions=total,
        recent_7d_predictions=recent,
        confidence_distribution=confidence_distribution,
        outcome_breakdown=outcome_breakdown,
        high_confidence_completion_rate=completion_rate,
        score_trend_recent=score_trend_recent,
        score_trend_all=score_trend_all,
        drift=drift,
        model_versions=model_versions,
    )


def _scalar(db: Session, query: str, params: dict) -> int:
    """Execute a query and return the scalar result (or 0 if None)."""
    return db.execute(sqltext(query), params).scalar() or 0
