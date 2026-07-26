# ML Plan: Next-Day Task Prediction

Status: Phase 3 complete, Phase 4 in progress
Last updated: 2026-07-26

## Goal

Build a practical ML feature that predicts the set of tasks that should appear in tomorrow's plan, using existing user history, backlog, daily plans, schedule items, activity events, and feedback.

## How to use this file

- Update `Status` for each checklist item as work progresses.
- Add short notes only when something is blocked, changed, or validated.
- Keep the order unless a dependency changes.

## Audit Summary

- Phase 1 is complete: sources, label rule, snapshot boundary, leakage risks, and data quality notes are confirmed.
- The next implementation step is Phase 2: build an offline snapshot extraction job for training data generation.
- Use user timezone for all day boundaries and convert end-of-day snapshots to UTC before querying.
- Treat sample 24h-block seed data as noisy and filter or down-weight it during training.
- Use `completed_at > end_of_D` instead of `status != completed` when deciding whether a task was completed at snapshot time.
- Current conclusion: data is ready for dataset building, but no training pipeline exists yet.
- `_get_user_context_features` has been optimized from 6 queries to 1 aggregate query.
- All 47 tests pass after the optimization, and the benchmark shows the hotspot time dropped from about `0.311s` to `0.125s` per snapshot.
- Phase 2 is fully closed: all blockers before Phase 3 are done and the realistic label verification passed with expected labels.
- Phase 3 is fully closed: baseline training pipeline, tests, artifact saving, and weighted LogisticRegression with ~33% F1 on synthetic data.
- Phase 4 comparison against rule-based baseline is complete: `scripts/rule_baseline.py` implements 6 heuristic scorers. On synthetic dataset (3,391 rows, 2.2% positive), **ML beats rule-based 9.6x F1** (0.33 vs 0.03), **2.4x AUROC** (0.96 vs 0.40). precision@1=1.0 (ML) vs 0.0 (rule-based).
- `scripts/generate_synthetic_dataset.py` creates a reproducible synthetic dataset with both labels (via backlog tasks pre-planned for D+1). Current output: `data/synthetic_training_dataset.parquet` (3,391 rows, 73 positive).
- Phase 4 is therefore partially complete: benchmark comparison is done, but error analysis and release threshold definition are still open before Phase 5.

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
| Review false positives and false negatives | Todo | Cần phân tích confusion matrix và error patterns trên synthetic dataset. | We understand common failure patterns. |
| Set release threshold | Todo |  | We know the minimum quality needed for integration. |

## Phase 5: Integration

| Item | Status | Notes | Done when |
| --- | --- | --- | --- |
| Add inference service | Todo |  | Backend can score candidate tasks for tomorrow. |
| Wire inference into plan generation | Todo |  | Tomorrow plan generation can use ML output. |
| Keep rule-based fallback | Todo |  | If model fails or confidence is low, the app still works. |
| Preserve current API shape | Todo |  | Frontend changes stay minimal. |
| Verify end-to-end flow | Todo |  | User can generate a plan and see predicted tasks. |

## Phase 6: Monitoring and Iteration

| Item | Status | Notes | Done when |
| --- | --- | --- | --- |
| Log prediction outputs | Todo |  | Scores, top-k predictions, and chosen plan are recorded. |
| Log user feedback signals | Todo |  | Completion, skip, delay, move, and edits are stored. |
| Track model quality over time | Todo |  | We can see drift and degradation. |
| Define retraining cadence | Todo |  | We know when and how the model will be refreshed. |
| Plan next model iteration | Todo |  | We have a concrete improvement backlog. |

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
