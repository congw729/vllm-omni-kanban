# vLLM-Omni Kanban — Implementation Plan

**Date:** 2026-03-13
**Status:** Ready to Execute
**References:** [PRD](2026-03-13-prd.md) · [Architecture](2025-03-13-kanban-design.md) · [TDD Plan](2025-03-13-tdd-plan-design.md)

---

## Execution Order

TDD discipline is enforced throughout: **write tests first, then implement**. Each task below follows the Red → Green → Refactor cycle.

---

## Phase 1: Foundation (Week 1)

### 1.1 Repo Scaffold

**Files to create:**

| File | Purpose |
|------|---------|
| `requirements.txt` | Python deps: mkdocs-material, mkdocs-macros-plugin, jsonschema, requests, freezegun, pytest, pytest-cov, pytest-mock, responses |
| `pytest.ini` | Test runner config |
| `mkdocs.yml` | MkDocs with Material theme, macros plugin, ECharts JS |
| `data/config.json` | All 5 models × 5 hardware × global thresholds |
| `data/index.json` | Empty initial index |
| `data/alerts.json` | Empty initial alert history |
| `docs/index.md` | Dashboard homepage skeleton |
| `docs/overrides/main.html` | ECharts JS injection override |
| `docs/assets/js/render_charts.js` | ECharts mount script |
| `scripts/fetch_latest_results.py` | Scheduled fetch from external daily results source |

**Tasks:**
- [ ] Create directory structure matching repo layout in design doc
- [ ] Write `data/config.json` with all 5 models (including `Qwen-Image-edit`, `WAN2.2`, `Qwen3-Omni`, `Qwen3-TTS`, `Qwen-image`), all 5 hardware platforms, global thresholds, and per-model `alert_overrides`
- [ ] Write `requirements.txt`
- [ ] Write `pytest.ini`
- [ ] Define secrets/config contract for `RESULTS_SOURCE_URL` and `RESULTS_SOURCE_TOKEN`
- [ ] Verify `mkdocs serve` starts without errors

### 1.2 `process_results.py`

**TDD order:**

1. `test_validate_schema_valid` / `test_validate_schema_missing_required` → implement `validate_result(data, config)`
2. `test_validate_schema_invalid_type` / `test_validate_schema_unknown_hardware` → extend validator
3. `test_first_run_no_data_dir` → implement directory creation on first run
4. `test_creates_date_file_if_missing` → implement `write_result(result, data_dir)`
5. `test_append_result` → implement append-to-existing-date-file logic
6. `test_updates_index_json` → implement `update_index(data_dir)`
7. `test_deduplicate_same_payload` / `test_upsert_same_day_tuple_from_scheduled_fetch` → enforce one snapshot per `(date, hardware, model)`
8. `test_prune_old_data` + `test_prune_boundary` → implement 90-day prune
9. `test_generate_daily_report` + `test_daily_report_content` → implement `generate_report(date, results, config)`
10. `test_validate_only_flag` → implement `--validate-only` CLI flag

**Script interface:**
```bash
python scripts/process_results.py [--validate-only] [--input FILE] [--source dispatch|schedule]
# Reads from: github.event.client_payload (injected as env) or --input file containing one result or a daily batch
# Writes to: data/results/YYYY-MM-DD.json, data/index.json, docs/reports/YYYY-MM-DD.md
```

**Coverage gate:** ≥80% before moving to Phase 2.

---

## Phase 2: Alerting (Week 2)

### 2.1 `check_alerts.py`

**TDD order (strict — 95% coverage required):**

1. `test_absolute_pass_rate_critical` / `test_absolute_pass_rate_warning` → implement `check_absolute_thresholds(result, config)`
2. `test_absolute_latency_critical` / `test_absolute_crash_count_critical` → extend absolute checks
3. `test_no_false_positives` → confirm no spurious alerts on healthy data
4. `test_regression_latency_p99` / `test_regression_throughput` → implement `check_regression(result, baseline, config)`
5. `test_sparse_baseline_skips_regression` → handle < 7 days gracefully
6. `test_per_model_threshold_override` → apply `alert_overrides` from config
7. `test_alert_cooldown_suppresses` / `test_alert_cooldown_expires` → implement cooldown in `alerts.json`
8. `test_alert_cooldown_resets_on_recovery` → reset on metric recovery
9. `test_alert_format_critical` / `test_alert_format_regression` → implement `format_alert_message(alert)`
10. `test_alert_history_written` → write triggered alerts to `alerts.json`
11. `test_send_wechat_success` / `test_send_wechat_failure` → implement `send_wechat(message, webhook_url)`
12. `test_send_email_success` / `test_send_email_failure` → implement `send_email(message, smtp_config)`
13. `test_no_notifications_when_no_alerts` → confirm notification functions not called unnecessarily

**Script interface:**
```bash
python scripts/check_alerts.py
# Reads from: data/results/ (latest date), data/index.json, data/config.json, data/alerts.json
# Writes to: data/alerts.json
# Sends: WeChat webhook, Email SMTP (via env vars)
```

**Coverage gate:** ≥95% before moving to Phase 3.

---

## Phase 3: Dashboard & Visualization (Week 3)

### 3.1 `generate_charts.py`

**TDD order:**

1. `test_line_chart_data_structure` → implement `build_line_chart(metric, dates, data)`
2. `test_line_chart_7d_window` / `test_line_chart_30d_window` → implement date range filter
3. `test_heatmap_matrix_shape` / `test_heatmap_matrix_values` → implement `build_heatmap(data, config)`
4. `test_heatmap_missing_cell` → handle missing combinations with null
5. `test_bar_chart_per_model` → implement `build_bar_chart(model, metric, data)`
6. `test_empty_data_handling` → handle empty input gracefully
7. `test_output_files_created` → implement file writing to `docs/assets/charts/`

**Script interface:**
```bash
python scripts/generate_charts.py
# Reads from: data/results/ + data/index.json
# Writes to: docs/assets/charts/*.json
```

**Coverage gate:** ≥80% before moving to Phase 4.

### 3.2 Dashboard Homepage

**Files to implement:**

| File | Content |
|------|---------|
| `docs/index.md` | Summary cards, hardware grid, model matrix, trend chart macros, recent alerts |
| `docs/overrides/main.html` | Extends Material base, injects ECharts + render_charts.js |
| `docs/assets/js/render_charts.js` | Reads `*.json` from assets/charts/, mounts each ECharts instance |

**Tasks:**
- [ ] Implement summary card section (overall pass rate, avg latency, latest commit)
- [ ] Implement hardware status grid (5 cards with pass/fail color coding)
- [ ] Implement model × hardware matrix table
- [ ] Wire `{{ render_chart("...") }}` macros to ECharts JSON files
- [ ] Verify charts render correctly in `mkdocs serve`

---

## Phase 4: CI Integration (Week 4)

### 4.1 GitHub Actions Workflows

**Files to create:**

| File | Purpose |
|------|---------|
| `.github/workflows/process-results.yml` | Three-job workflow: process / alert / deploy with scheduled fetch support |
| `.github/workflows/build-dashboard.yml` | Manual MkDocs rebuild/deploy |

**Tasks:**
- [ ] Implement `process-results.yml` with three jobs as specified in the design doc
- [ ] Add scheduled fetch step that runs `scripts/fetch_latest_results.py` at 6:00 AM Beijing time
- [ ] Add `--validate-only` step before write in the `process` job
- [ ] Confirm `repository_dispatch` trigger works with `event_type: ci_results`
- [ ] Confirm `schedule: cron: '0 22 * * *'` fires at 6:00 AM Beijing time and fetches the full daily batch
- [ ] Add `git config user.email` to commit steps (required by git)
- [ ] Commit generated chart JSON in the `process` job before downstream deploy
- [ ] Commit `data/alerts.json` in the `alert` job so the dashboard shows current alert history
- [ ] Make `deploy` depend on `alert`, not just `process`
- [ ] Document required GitHub Secrets: `KANBAN_TOKEN`, `RESULTS_SOURCE_URL`, `RESULTS_SOURCE_TOKEN`, `WECHAT_WEBHOOK`, `EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USER`, `EMAIL_SMTP_PASS`, `EMAIL_FROM`, `EMAIL_TO`

### 4.2 Scheduled Fetch Script

**TDD order:**

1. `test_fetch_latest_results_success` → implement successful download of daily batch JSON
2. `test_fetch_latest_results_auth_header` → include optional bearer token
3. `test_fetch_latest_results_retries_transient_error` → retry on transient HTTP failure
4. `test_fetch_latest_results_invalid_payload` → reject malformed batch structure
5. `test_fetch_latest_results_writes_output_file` → persist batch JSON to requested output path

**Script interface:**
```bash
python scripts/fetch_latest_results.py --output /tmp/daily-results.json
# Reads from: RESULTS_SOURCE_URL, optional RESULTS_SOURCE_TOKEN
# Writes to: batch JSON for the current daily snapshot
```

### 4.3 End-to-End Smoke Test

- [ ] Create `tests/fixtures/sample_dispatch_payload.json` with a realistic CI result
- [ ] Create `tests/fixtures/sample_daily_batch.json` with all 5 models × 5 hardware combinations
- [ ] Run `python scripts/process_results.py --input tests/fixtures/sample_dispatch_payload.json --source dispatch` locally
- [ ] Run `python scripts/process_results.py --input tests/fixtures/sample_daily_batch.json --source schedule` locally
- [ ] Verify `data/results/YYYY-MM-DD.json` created, `data/index.json` updated, `docs/reports/YYYY-MM-DD.md` generated
- [ ] Run `python scripts/generate_charts.py` and verify `docs/assets/charts/*.json` created
- [ ] Run `python scripts/check_alerts.py` and verify `data/alerts.json` updated
- [ ] Run `mkdocs serve` and manually verify homepage renders with data

---

## Phase 5: Polish & Docs (Week 5)

### 5.1 Navigation & Search

- [ ] Add `mkdocs.yml` nav section: Home, Reports (index of dated pages), Alerts
- [ ] Add `docs/reports/index.md` — auto-generated list of all report links
- [ ] Verify MkDocs search indexes daily reports

### 5.2 Integration Tests

- [ ] Implement `tests/integration/test_pipeline.py` (5 tests as defined in TDD plan)
- [ ] Run full integration suite; fix any failures

### 5.3 Documentation

- [ ] Add `docs/contributing.md` — how to add a new model, metric, hardware platform
- [ ] Add `docs/alerts.md` — alert history page rendering from `alerts.json`
- [ ] Add ops documentation for the external results source contract and rotation procedure for related secrets
- [ ] Update `README.md` — add link to live dashboard URL once deployed

### 5.4 Final Checks

- [ ] Run `pytest --cov=scripts --cov-fail-under=80`
- [ ] Run `pytest tests/unit/test_check_alerts.py --cov=scripts/check_alerts --cov-fail-under=95`
- [ ] Run `mkdocs build --strict` (no warnings)
- [ ] Manually trigger `repository_dispatch` and verify full pipeline runs end-to-end
- [ ] Confirm WeChat and Email notifications received

---

## Dependency Graph

```
config.json (data schema)
      │
      ▼
fetch_latest_results.py
      │
      ▼
process_results.py  ──────────────────────────────┐
      │                                            │
      ▼                                            ▼
data/results/*.json                       docs/reports/*.md
      │
      ├─────────────────────────────┐
      ▼                             ▼
check_alerts.py               generate_charts.py
      │                             │
      ▼                             ▼
data/alerts.json + notifications    docs/assets/charts/*.json
      │
      ▼
mkdocs build → GitHub Pages
```

---

## Risk Register

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| `repository_dispatch` payload > 10KB | Medium | High | One dispatch per result; validate payload size in CI |
| External results source unavailable at 6:00 AM | Medium | High | Retry fetch, alert on failure, keep previous day visible until refreshed |
| ECharts rendering fails on GitHub Pages | Low | Medium | Test with `mkdocs serve` before deploying; use CDN fallback |
| Concurrent CI pushes corrupt date file | Low | High | Atomic write (write to temp file, rename); CI serialization |
| WeChat webhook deprecated/changed | Low | Medium | Abstract notification behind interface; easy to swap |
| Sparse data causes false regression alerts | Medium | Medium | Implemented: skip regression check if < 7 days baseline |
