from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

__all__ = ["TaskPrediction", "PredictionResult", "MLMonitoringResponse"]


class TaskPrediction(BaseModel):
    """Prediction for a single candidate task."""

    task_id: str
    score: float = Field(ge=0.0, le=1.0)
    confidence_band: str = Field(
        default="low",
        description="One of 'high' (>=0.70), 'medium' (>=0.40), 'low' (<0.40)",
    )


class PredictionResult(BaseModel):
    """Result of a batch ML prediction call."""

    model_config = ConfigDict(protected_namespaces=())

    predictions: list[TaskPrediction] = Field(default_factory=list)
    result_status: str = Field(
        default="ok",
        description="One of 'ok', 'fallback_model_missing', 'fallback_prediction_error', 'fallback_empty_input'",
    )
    classifier_type: str = Field(default="", description="Classifier type, e.g. LogisticRegression")
    n_candidates: int = 0
    n_scored: int = 0
    n_high_confidence: int = 0
    n_medium_confidence: int = 0
    fallback_used: bool = False


class BandDistribution(BaseModel):
    """Confidence band summary for monitoring."""

    band: str
    count: int
    percentage: float
    avg_score: float


class OutcomeBreakdown(BaseModel):
    """Outcome summary for monitoring."""

    outcome: str
    count: int
    percentage: float


class ScoreTrend(BaseModel):
    """Score trend for a time period."""

    period: str
    avg_score: float
    min_score: float
    max_score: float
    count: int


class DriftSignal(BaseModel):
    """Drift indicator comparing recent vs all-time scores."""

    recent_avg: float
    all_time_avg: float
    drift_pct: float
    alert: bool


class ModelVersionSummary(BaseModel):
    """Model version usage summary."""

    model_version: str
    model_type: str
    count: int
    percentage: float


class MLMonitoringResponse(BaseModel):
    """Response from the ML monitoring endpoint."""

    total_predictions: int
    recent_7d_predictions: int
    confidence_distribution: list[BandDistribution]
    outcome_breakdown: list[OutcomeBreakdown]
    high_confidence_completion_rate: float | None = None
    score_trend_recent: ScoreTrend | None = None
    score_trend_all: ScoreTrend | None = None
    drift: DriftSignal | None = None
    model_versions: list[ModelVersionSummary]
