# vLLM-Omni Kanban TDD Plan

**Date:** 2025-03-13
**Last Updated:** 2026-03-13
**Status:** Approved (v2 — revised)
**Author:** Brainstorming session

## Overview

Test-Driven Development plan for vLLM-Omni Kanban using pytest. Focus on core Python scripts with fixtures-based testing. Alerting logic requires ≥95% coverage; overall target ≥80%.

## 1. Test Structure

```
vllm-omni-kanban/
├── tests/
│   ├── conftest.py                  # Shared fixtures (sample CI data)
│   ├── unit/
│   │   ├── test_process_results.py  # Unit tests for data processing
│   │   ├── test_fetch_latest_results.py # Unit tests for scheduled external fetch
│   │   ├── test_generate_charts.py  # Unit tests for chart generation
│   │   └── test_check_alerts.py     # Unit tests for alerting logic
│   └── integration/
│       └── test_pipeline.py         # End-to-end pipeline tests
├── pytest.ini                       # pytest configuration
└── requirements.txt                 # includes pytest, pytest-cov, pytest-mock
```

## 2. Test Fixtures (`conftest.py`)

Sample CI result fixtures covering:

- `valid_minimal`: bare minimum required fields only
- `valid_full`: all fields populated (all 5 models, all 5 hardware)
- `edge_cases`: missing optional fields, extreme values (0%, 100%, very high latency)
- `invalid`: malformed data for schema validation tests
- `duplicate`: exact duplicate payload for an existing `(date, hardware, model)` snapshot
- `scheduled_replacement`: newer scheduled-fetch payload for an existing `(date, hardware, model)` snapshot
- `daily_batch`: one full daily batch (5 hardware × 5 models)
- `multi_hardware`: 5 hardware types × 5 models matrix (25 entries)
- `time_series_7d`: 7 days of data for regression baseline tests
- `time_series_sparse`: only 2 days of data (tests sparse baseline handling)
- `first_run`: empty `data/results/` directory (no prior data)

Key fixtures:

| Fixture | Purpose |
|---------|---------|
| `sample_ci_result` | Single valid result (H100 + Qwen3-TTS) |
| `sample_daily_batch` | Full daily snapshot batch used by scheduled fetch path |
| `sample_date_file` | Per-date JSON structure with 3 results |
| `sample_index` | `index.json` with 5 recent dates |
| `sample_config` | Full config with all 5 models, 5 hardware, global + per-model thresholds |
| `regression_baseline` | 7-day averages per (hardware, model, metric) |
| `sparse_baseline` | Only 2 days of data — insufficient for regression |
| `alert_history` | `alerts.json` with one active suppressed alert |
| `mock_fetch_response` | HTTP fixture for external results source payload |
| `tmp_data_dir` | Temporary directory simulating `data/results/` (pytest tmp_path) |

## 3. Test Cases by Script

### `test_process_results.py`

| Test | Description |
|------|-------------|
| `test_append_result` | New result appends to correct date file |
| `test_creates_date_file_if_missing` | Creates `YYYY-MM-DD.json` on first result for that date |
| `test_first_run_no_data_dir` | Handles missing `data/results/` directory gracefully (creates it) |
| `test_updates_index_json` | `index.json` updated with new date after append |
| `test_prune_old_data` | Date files older than 90 days are deleted |
| `test_prune_updates_index` | Pruned dates removed from `index.json` |
| `test_prune_boundary` | Exactly 90-day-old data is retained; 91-day-old data is deleted |
| `test_deduplicate_same_payload` | Exact duplicate payload for the same daily snapshot is ignored, logs warning |
| `test_upsert_same_day_tuple_from_scheduled_fetch` | Scheduled fetch replaces an existing snapshot for the same `(date, hardware, model)` when newer data arrives |
| `test_deduplicate_different_hardware` | Same model + date but different hardware → both appended |
| `test_validate_schema_valid` | Valid result passes validation without error |
| `test_validate_schema_missing_required` | Missing required field raises `ValidationError` |
| `test_validate_schema_invalid_type` | Wrong type for field raises `ValidationError` |
| `test_validate_schema_unknown_hardware` | Hardware not in config raises `ValidationError` |
| `test_validate_schema_unknown_model` | Model not in config raises `ValidationError` |
| `test_generate_daily_report` | Markdown report generated at `docs/reports/YYYY-MM-DD.md` |
| `test_daily_report_content` | Report contains commit SHA, pass rate, per-hardware table |
| `test_handle_missing_optional_fields` | Missing optional metrics don't crash report generation |
| `test_validate_only_flag` | `--validate-only` flag validates without writing any files |
| `test_process_batch_input` | Scheduled batch file with 25 results is processed successfully |

### `test_fetch_latest_results.py`

| Test | Description |
|------|-------------|
| `test_fetch_latest_results_success` | External daily batch JSON is downloaded successfully |
| `test_fetch_latest_results_auth_header` | Optional bearer token is sent when configured |
| `test_fetch_latest_results_retries_transient_error` | Transient HTTP error is retried before succeeding |
| `test_fetch_latest_results_invalid_payload` | Malformed batch payload raises validation error |
| `test_fetch_latest_results_writes_output_file` | Batch JSON is written to requested output path |
| `test_fetch_latest_results_timeout` | Request timeout is logged and surfaced clearly |

### `test_generate_charts.py`

| Test | Description |
|------|-------------|
| `test_line_chart_data_structure` | Time series output is valid ECharts option JSON |
| `test_line_chart_7d_window` | 7-day filter returns exactly 7 data points |
| `test_line_chart_30d_window` | 30-day filter returns up to 30 data points |
| `test_heatmap_matrix_shape` | Model × Hardware matrix has correct dimensions (5×5) |
| `test_heatmap_matrix_values` | Cell values are pass rates in [0.0, 1.0] |
| `test_heatmap_missing_cell` | Missing (model, hardware) combination renders as null/empty |
| `test_bar_chart_per_model` | Bar chart groups data correctly for a single model across hardware |
| `test_empty_data_handling` | Returns empty chart structure (no crash) when no data |
| `test_single_day_data` | Works correctly when only 1 day of data is available |
| `test_date_range_filtering` | Data outside date range is excluded |
| `test_output_files_created` | JSON files written to `docs/assets/charts/` |

### `test_check_alerts.py`

| Test | Description |
|------|-------------|
| `test_absolute_pass_rate_critical` | Pass rate < 0.80 triggers critical alert |
| `test_absolute_pass_rate_warning` | Pass rate < 0.90 (but ≥ 0.80) triggers warning alert |
| `test_absolute_pass_rate_ok` | Pass rate ≥ 0.90 triggers no alert |
| `test_absolute_latency_critical` | Latency P99 > 1000ms triggers critical alert |
| `test_absolute_crash_count_critical` | Crash count ≥ 3 triggers critical alert |
| `test_regression_latency_p99` | P99 +25% vs 7-day baseline triggers regression alert |
| `test_regression_throughput` | Throughput −20% vs 7-day baseline triggers regression alert |
| `test_regression_pass_rate` | Pass rate −6% vs 7-day baseline triggers regression alert |
| `test_regression_below_threshold` | P99 +10% (below 20% threshold) does not trigger alert |
| `test_no_false_positives` | All metrics within normal range → no alerts |
| `test_sparse_baseline_skips_regression` | < 7 days of data → regression check skipped, no false alert |
| `test_alert_cooldown_suppresses` | Same alert within 24h of first trigger is suppressed |
| `test_alert_cooldown_resets_on_recovery` | After metric recovers, cooldown resets |
| `test_alert_cooldown_expires` | Alert fires again after 24h cooldown expires |
| `test_per_model_threshold_override` | Per-model threshold in config overrides global default |
| `test_alert_format_critical` | Critical notification message matches expected format |
| `test_alert_format_regression` | Regression notification message includes before/after values |
| `test_alert_history_written` | Triggered alert is recorded in `alerts.json` |
| `test_send_wechat_success` | WeChat webhook called with correct payload (mocked HTTP) |
| `test_send_wechat_failure` | WeChat webhook HTTP error is logged, does not crash pipeline |
| `test_send_email_success` | SMTP send called with correct args (mocked smtplib) |
| `test_send_email_failure` | SMTP failure is logged, does not crash pipeline |
| `test_no_notifications_when_no_alerts` | Notification functions not called if no alerts triggered |

### `test_pipeline.py` (Integration)

| Test | Description |
|------|-------------|
| `test_full_pipeline_happy_path` | Push valid result → date file created → index updated → report generated → chart JSON written |
| `test_full_pipeline_scheduled_fetch_path` | Fetch daily batch → process batch → generate alerts/charts → persist outputs |
| `test_full_pipeline_triggers_alert` | Push result with pass_rate=0.70 → alert record in `alerts.json` |
| `test_full_pipeline_first_run` | Pipeline runs cleanly on empty repo (no prior data) |
| `test_full_pipeline_dedup` | Push same result twice → only one daily snapshot remains in date file |
| `test_full_pipeline_scheduled_fetch_replaces_daily_snapshot` | Scheduled fetch updates an existing same-day snapshot instead of appending a second one |
| `test_full_pipeline_90day_prune` | After pushing data, files > 90 days are removed and index updated |

## 4. TDD Workflow Per Script

Cycle per feature:

```
1. Write failing test → 2. Write minimal code → 3. Test passes → 4. Refactor
         ↑                                                        |
         +--------------------------------------------------------+
```

Implementation order:

| Phase | Script | Why First |
|-------|--------|-----------|
| 1 | `process_results.py` | Core data layer — everything depends on it |
| 2 | `check_alerts.py` | Business logic, independent of visualization |
| 3 | `generate_charts.py` | Depends on processed data format |
| 4 | `fetch_latest_results.py` | External ingestion path depends on validated batch contract |
| 5 | Integration tests | Requires all scripts and both ingestion paths to be working |

Per-phase checklist:

- [ ] Write tests for one function/feature
- [ ] Run `pytest -x` (confirm fail)
- [ ] Implement minimal code to pass
- [ ] Run `pytest` (confirm pass)
- [ ] Refactor if needed
- [ ] Repeat for next feature

## 5. Test Commands & Coverage

**`pytest.ini`:**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v --tb=short
```

**Commands:**

```bash
# Run all tests
pytest

# Run with coverage report
pytest --cov=scripts --cov-report=term-missing

# Run unit tests only
pytest tests/unit/

# Run integration tests only
pytest tests/integration/

# Run specific test file
pytest tests/unit/test_process_results.py
pytest tests/unit/test_fetch_latest_results.py

# Run single test
pytest tests/unit/test_process_results.py::test_append_result

# Run with coverage thresholds enforced
pytest --cov=scripts --cov-fail-under=80
pytest tests/unit/test_check_alerts.py --cov=scripts/check_alerts --cov-fail-under=95
```

## 6. Coverage Targets

| Script | Minimum Coverage | Rationale |
|--------|-----------------|-----------|
| `process_results.py` | 80% | Data plumbing — well-defined paths |
| `fetch_latest_results.py` | 80% | External ingress path — source failures must be handled predictably |
| `generate_charts.py` | 80% | Visualization — format correctness |
| `check_alerts.py` | **95%** | Business-critical — missed alert = undetected regression |
| Overall | 80% | Baseline quality gate |

## 7. Mocking Strategy

| Dependency | Mock Approach |
|-----------|---------------|
| WeChat webhook HTTP call | `pytest-mock` / `responses` library to mock `requests.post` |
| External results source HTTP call | `responses` library to mock batch download, auth, retries, and timeouts |
| SMTP email sending | Mock `smtplib.SMTP` context manager |
| File system (date files, index) | `pytest` `tmp_path` fixture for isolated temp directories |
| Current date/time | `freezegun` library to fix time for cooldown and pruning tests |
| GitHub Actions environment | Set env vars in test via `monkeypatch.setenv` |
