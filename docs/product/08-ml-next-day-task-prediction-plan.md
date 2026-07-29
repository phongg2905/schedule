# ML Plan: Next-Day Task Prediction

Status: Active planning and validation doc
Last validated: 2026-07-29

## Goal

Predict which tasks should appear in tomorrow's plan using user history, backlog, schedules, activity events, and feedback.

## Current Focus

- Keep the ML feature practical and safe rather than turning it into a separate product
- Preserve the rule-based fallback when the model is missing or confidence is low
- Keep synthetic and retrained artifacts available for staging and comparison
- Track release readiness separately in `docs/release/RC1-QA.md`

## How to use this file

- Treat the section below as an audit trail and implementation history
- Revalidate any numeric claim before using it as current status
- Update only the top summary when the current state changes

## Historical Audit Summary

- The notes below were written during the original ML buildout
- They are preserved for reference and may contain dated counts, benchmark numbers, or status labels
- Do not treat them as current release status unless they have been rechecked

## Phase 6: Monitoring Feedback & Drift

| Item | Status | Notes | Done when |
| --- | --- | --- | --- |
| ML prediction logging table | Done | `ml_prediction_logs` table logs each prediction with score, band, model_version, model_type, plan_id, task_id. Outcome field filled asynchronously via reconciliation. | Each `predict_result()` call creates rows in `ml_prediction_logs`. |
| Model version tracking | Done | `MLPredictionService.model_version` property reads from `metadata.json` timestamp. Written to each log row. | Every log entry includes the model version. |
| Prediction logging in plan generation | Done | `DailyPlanService._generate_internal()` calls `ml_service.log_predictions()` after ML scoring, best-effort. | ML predictions are logged during every plan generation. |
| Monitoring script | Done | `scripts/monitor_ml_predictions.py` — reports confidence distribution, outcome breakdown, score trend, drift signal. | A CLI report can be generated on demand or periodically. |
| Migration | Done | `migrations/versions/0004_add_ml_prediction_logs.py` — adds the new table. | Alembic migration exists and can be applied to any environment. |
| Outcome reconciliation script | Done | `scripts/reconcile_ml_outcomes.py` — batch-reconciles `MLPredictionLog.outcome` against `ActivityEvent` records. Supports dry-run mode and both SQLite/PostgreSQL. | Reconciliation can be run on demand or scheduled. |
| Monitoring API endpoint | Done | `GET /api/v1/ml/monitoring` returns confidence distribution, outcome breakdown, high-confidence completion rate, score trends, drift signal, and model version summary for the authenticated user. | Stats are queryable at runtime without DB access. |
| STAGING_STRATEGY env var | Done | `STAGING_STRATEGY=synthetic|retrained` env var controls which model directory is used. `MLPredictionService(strategy=...)` auto-resolves paths. Falls back gracefully on unknown or missing strategy. | A/B staging between synthetic and retrained models. |
| Retrain trigger policy | Done | Triggers: (a) mean score drift >10% sustained over 7 days, (b) volume-based retrain every 10,000 predictions, (c) manual trigger. Monitored via `GET /api/v1/ml/monitoring` or `scripts/monitor_ml_predictions.py`. | Documented thresholds for automated retraining alert. |
| Production model decision | Done | Default: **synthetic model** (F1=0.33) for recommendation quality. `STAGING_STRATEGY=retrained` for A/B testing in staging. Promotion criteria: retrained model achieves F1 > 0.20 on real feedback data (monitored via MLPredictionLog outcomes). | Decision documented, env var ready, monitoring in place. |

### Phase 6 Components

| Component | Location | Description |
|-----------|----------|-------------|
| MLPredictionLog model | `src/db/models.py` | Tracks each prediction: score, band, model_version, model_type, plan_id, task_id, outcome |
| Migration 0004 | `migrations/versions/0004_add_ml_prediction_logs.py` | Creates `ml_prediction_logs` table |
| log_predictions() | `src/modules/ml/prediction_service.py` | Bulk-inserts predictions into MLPredictionLog during plan generation |
| model_version property | `src/modules/ml/prediction_service.py` | Reads version from `metadata.json` timestamp, written to each log entry |
| Monitoring API | `GET /api/v1/ml/monitoring` | Returns confidence distribution, outcome breakdown, score trend, drift signal |
| Monitoring script | `scripts/monitor_ml_predictions.py` | CLI report with same stats as API, supports --db and --settings flags |
| Reconcile script | `scripts/reconcile_ml_outcomes.py` | Matches MLPredictionLog against ActivityEvent to fill outcome field, supports dry-run |
| STAGING_STRATEGY | `.env` config | `synthetic` (default) or `retrained`. Resolves model directory paths in `MLPredictionService`. |

### STAGING_STRATEGY Usage

```bash
# .env or environment variable
STAGING_STRATEGY=synthetic     # default — uses models/synthetic/
STAGING_STRATEGY=retrained     # uses models/retrained/ for A/B testing
```

The strategy is read by `DailyPlanService` via `get_settings().staging_strategy` and passed to `MLPredictionService(strategy=...)`. If the requested strategy directory is missing, it falls back to synthetic with a warning. Each prediction logged includes `model_version` and `model_type`, so monitoring reports can distinguish between strategies.

### Production Model Decision

| Criterion | Synthetic model (default) | Retrained model |
|-----------|--------------------------|-----------------|
| F1 score | **0.33** ✓ | 0.13 |
| AUROC | 0.96 | **0.98** ✓ |
| Positive ratio | 2.2% (less realistic) | **0.69%** (more realistic) ✓ |
| Dataset size | 3,391 rows | **10,616 rows** ✓ |
| Training data | Pure synthetic | 24h routine + backlog mix ✓ |
| Recommendation quality | **Better** ✓ | Worse (diluted by many routine tasks) |

**Recommendation:** Keep the synthetic model as the production default. Use `STAGING_STRATEGY=retrained` in staging to collect real feedback data. Only promote the retrained model to production if monitoring shows its F1 exceeds 0.20 on reconciled outcomes.

### Monitoring & Retrain Policy

1. **Check `GET /api/v1/ml/monitoring` or run `scripts/monitor_ml_predictions.py`** to review:
   - Score distribution shifts
   - High-confidence completion rate (target: >50%)
   - Mean score drift (>10% triggers alert)
2. **Run `scripts/reconcile_ml_outcomes.py` periodically** (e.g., hourly cron) to fill outcome fields:
   ```bash
   python scripts/reconcile_ml_outcomes.py --settings    # load from app config
   python scripts/reconcile_ml_outcomes.py --dry-run     # preview only
   ```
3. **Retrain triggers:**
   - Drift-based: mean score shift >10% sustained over 7 days (visible in drift.alert field)
   - Volume-based: every 10,000 new predictions logged
   - Manual: when feature engineering changes or new data sources available
4. **A/B staging:** deploy two instances with `STAGING_STRATEGY=synthetic` and `STAGING_STRATEGY=retrained`, then compare high-confidence completion rates via the monitoring endpoint.

## Label Distribution Findings

- Total rows: `2,792`
- Positive labels: `96` (`3.44%`)
- Negative labels: `2,696` (`96.56%`)
- Imbalance ratio: `28.1 : 1` negative to positive
- Temporal coverage is narrow in the sample data, so time-based split must be used instead of random shuffle
- The sample dataset is uniform enough that raw correlation is weak, which means baseline quality will depend more on clean feature engineering and imbalance handling than on model complexity
- Recommended training setup:
  - `scale_pos_weight = 28.1` or equivalent class weighting
  - no accuracy as the primary metric
  - use `precision@k`, `recall@k`, `F1`, and `Jaccard overlap`
  - keep a rule-based fallback for low-confidence predictions

## Phase 1: Data Audit

| Item | Status | Notes | Done when |
| --- | --- | --- | --- |
| Confirm source tables and fields | Done | tasks, daily_plans, schedules, schedule_items, activity_events, feedback, context_snapshots, day_summaries, user_schedule_preferences, users đều có dữ liệu dùng được. | We know which columns are available in tasks, daily_plans, schedules, schedule_items, activity_events, and feedback. |
| Define snapshot boundary | Done | D = end of day trong timezone user. Chỉ dùng data có created_at/occurred_at/updated_at <= end_of_D. Dùng completed_at để check nếu task completed sau D thì coi như chưa complete. | We only use data available at or before the end of day D. |
| Define label source | Done | Label = 1 nếu task có daily_plan_id trỏ vào DailyPlan cho D+1 và status ∈ {planned, completed}. Hoặc tồn tại ScheduleItem trong schedule của D+1 plan. | We can reliably identify which tasks were included in D+1 plan. |
| Check timezone handling | Done | users.timezone lưu IANA tz (mặc định Asia/Saigon). plans lưu plan_date dạng YYYY-MM-DD string — mặc nhiên theo timezone user. Snapshot cần chuyển end_of_D về UTC để query. | Date boundaries are consistent with user timezone. |
| Check missing values and noise | Done | Xem chi tiết bên dưới. | We know the null and inconsistent-field patterns. |

## Phase 2: Dataset Build

| Item | Status | Notes | Done when |
| --- | --- | --- | --- |
| Design training row schema | Done | 45 columns: task meta, status history, user context, temporal features. | Each row represents one candidate task at one snapshot date. |
| Build snapshot extraction job | Done | `scripts/build_ml_dataset.py` — CLI, PostgreSQL+SQLite, timezone-aware, batch queries. | We can generate day-level snapshots from historical DB data. |
| Build label assignment job | Done | `_get_plan_for_date` cached at snapshot level; `_get_label` uses pre-fetched daily_plan_id. | Each candidate task gets a positive or negative label for tomorrow. |
| Prevent leakage in extraction | Done | `assigned_plan_date` LEFT JOIN prevents daily_plan_id label leakage. `completed_at > end_of_D`. All filters use snapshot boundary. | No feature uses data after snapshot date D. |
| Export dataset artifact | Done | Parquet with zstd compression. 5,016 rows from reseeded sample data (29 days, 1 user). | We can write a reproducible parquet/csv dataset for training. |

### Verification results

| Metric | Value |
|--------|-------|
| Dataset rows | 5,016 |
| Snapshot range | July 7 → July 25 (19 days) |
| Target range | July 8 → July 26 |
| Avg tasks/snapshot | 264 |
| Output file | `data/full_training_dataset.parquet` (38.1 KB) |
| Labels | All 0 (expected — sample data uses per-day tasks, not backlog) |

### Seed data status

| Metric | Value |
|--------|-------|
| Seed script | `scripts/reseed_ml_ready_data.py` (deterministic timestamps) |
| Tasks | 696 (29 days x 24 tasks) |
| daily_plan_id coverage | 100% |
| Plans | 29 (July 6 → August 3) |
| created_at | Midnight UTC of each plan_date (deterministic) |

### Blockers trước Phase 3

- [x] Add automated tests for snapshot extraction job (SQLite in-memory)
- [x] Validate label correctness with a small realistic scenario
- [x] Verify performance with larger dataset

## Phase 3: Baseline Training

| Item | Status | Notes | Done when |
| --- | --- | --- | --- |
| Pick baseline model | Done | Weighted LogisticRegression (class_weight='balanced', solver='lbfgs'). XGBoost/LightGBM có thể thêm sau nếu baseline không đủ mạnh. | We choose logistic regression or gradient boosting as the first model. |
| Implement feature pipeline | Done | `scripts/train_baseline.py` — ColumnTransformer: StandardScaler cho numeric, OneHotEncoder cho categorical (status_at_d), passthrough cho binary. | Numeric and categorical features are transformed consistently. |
| Train initial model | Done | Pipeline chạy được end-to-end. Trên seed data (100% label=0), tự động fallback sang DummyClassifier. Chờ real data để train thật. | A baseline model can be trained end to end on the dataset. |
| Calibrate prediction scores | Done | LogisticRegression trained with log-loss → probabilities calibrated by default. Git-based evaluation report ghi log_loss. | Model scores are usable as probabilities or ranking signals. |
| Save model artifact | Done | joblib dump gồm full pipeline (preprocessor + model). Feature groups, metadata, evaluation report đi kèm. | The model can be versioned and loaded for inference. |

## Phase 4: Evaluation

| Item | Status | Notes | Done when |
| --- | --- | --- | --- |
| Define offline metrics | Done | precision@k, recall@k, F1, AUROC, average_precision được tính trong `_compute_metrics`. | We measure precision@k, recall@k, F1, and Jaccard overlap. |
| Create validation split strategy | Done | Time-based split theo snapshot_date: N snapshot đầu cho train, phần còn lại cho val. | Time-based split avoids future leakage. |
| Compare against rule-based baseline | Done | `scripts/rule_baseline.py` — 6 heuristic scorers. So sánh trên synthetic dataset (3,391 rows, 2.2% positive). **ML thắng toàn diện**: F1=0.33 vs 0.03 (9.6x), AUROC=0.96 vs 0.40, precision@1=1.0 vs 0.0. | We know whether ML beats the current heuristic. |
| Review false positives and false negatives | Done | Xem phân tích chi tiết trong conversation. Pattern chính: FP do task mới (`task_age_days` thấp), FN do task flexible/low priority. precision@0.5=0.20, recall@0.5=0.92. | We understand common failure patterns. |
| Set release threshold | Done | **Primary**: AUROC>=0.80 ✅(0.96), precision@1>=0.80 ✅(1.0), F1>=0.20 ✅(0.33). **Confidence bands**: >=0.70 auto-include, 0.40-0.70 suggest, <0.40 fallback. | We know the minimum quality needed for integration. |

## Phase 5: Integration

| Item | Status | Notes | Done when |
| --- | --- | --- | --- |
| Add inference service | Done | `apps/backend/src/modules/ml/prediction_service.py` — `MLPredictionService` class with lazy model loading, 38-feature extraction (replicating build_ml_dataset), `predict()` and `predict_result()` methods, graceful fallback on all errors. 50 unit tests. | Backend can score candidate tasks for tomorrow. |
| Wire inference into plan generation | Done | Integrated into `DailyPlanService._generate_internal()` after `_list_candidate_tasks()`. Tasks re-ranked by confidence band: high (>=0.70) first, then medium (>=0.40), then low/unscored. Rule-based sort preserved within each band. ML metadata (status, scores, top-10) logged into `context_snapshot.context_payload`. | Tomorrow plan generation can use ML output. |
| Keep rule-based fallback | Done | Fallback triggers when: model file missing, prediction raises exception, all scores < 0.40, or tasks list empty. `plan.source` = "ml_boosted" when ML used, "rule_based" otherwise. Plan generation always succeeds regardless of ML state. | If model fails or confidence is low, the app still works. |
| Preserve current API shape | Done | No changes to any API route, request schema, or response schema. Only `context_snapshot.context_payload` enriched with `{"ml": {status, classifier, n_scored, n_high_confidence, n_medium_confidence, top_scores, fallback_used}}`. Frontend needs zero changes. | Frontend changes stay minimal. |
| Verify end-to-end flow | Done | 4 E2E integration tests (`TestDailyPlanMLIntegration`): (1) plan source = ml_boosted, (2) context snapshot has ML metadata with correct structure, (3) tasks ranked by score, (4) fallback to rule_based when model unavailable. 164 tests total pass (50 ML + 4 E2E + 110 existing). | User can generate a plan and see predicted tasks. |

### Phase 5 bugs fixed

- `_BACKEND_ROOT` path in `prediction_service.py`: was `parents[2]` (pointing to `src/`), fixed to `parents[3]` (correctly pointing to `apps/backend/`). Model artifact path now resolves to `models/synthetic/model_pipeline.joblib`.
- `test_daily_plan_flow.py` assertion relaxed to accept both `ml_boosted` and `rule_based` sources, and to not depend on task ordering (ML re-ranking changes it).


## Risks To Watch

- Data leakage from using post-snapshot information.
- Label noise from users manually changing plans.
- Severe class imbalance because most candidate tasks are negative.
- Cold start for new users with little history.
- Concept drift when user behavior changes over time.
- Sample-data uniformity can hide useful signal until real user behavior accumulates.

## Success Criteria

- The model can predict tomorrow's task set better than the rule-based baseline.
- The system can still generate a usable plan if the model is unavailable.
- Dataset generation is reproducible and free of leakage.
- Monitoring tells us when retraining is needed.
- Phase 5 integration keeps the API shape stable and adds safe fallback behavior.
- Production rollout should be staged because the retrained model improves realism but currently underperforms the older synthetic model on F1.
- Phase 6 provides: prediction logging, outcome reconciliation, monitoring endpoint, staging strategy env var, and retrain policy — all 170 tests pass.
