# vLLM-Omni Kanban Design Document

**Date:** 2025-03-13
**Last Updated:** 2026-03-13
**Status:** Approved (v2 — revised)
**Author:** Design brainstorming session

## Overview

vLLM-Omni Kanban is a monitoring dashboard that tracks stability, performance, and accuracy of vLLM multimodal models across different hardware platforms. It maintains one daily snapshot per model/hardware combination. The system refreshes the full daily snapshot at 6:00 AM Beijing time by fetching results from an external source and can also accept push-based updates from vLLM-omni CI during the day.

## Goals

- Provide visibility into model performance across hardware platforms
- Track daily CI results with 90-day historical retention
- Alert team when stability, performance, or accuracy degrades
- Archive daily reports for historical analysis

## Scope

### Models (Initial)
- Qwen-image
- Qwen-Image-edit
- WAN2.2
- Qwen3-Omni
- Qwen3-TTS

### Hardware Platforms
- NVIDIA A100
- NVIDIA H100
- NVIDIA H20
- AMD MI300X
- Ascend NPU A2/A3

### Metrics
- **Stability:** pass rate, crash count, error types
- **Performance:** latency (p50, p99), throughput, TTFT
- **Accuracy:** benchmark scores, quality metrics
- **Custom:** per-model specific metrics (extensible)

## Architecture

### Approach: Hybrid Push + Scheduled Fetch Pipeline

```
vLLM-omni CI --(push single result)----------------------+
                                                         |
External results source --(6:00 AM fetch daily batch)--> [fetch_latest_results.py]
                                                         |
                                                         v
                                                   [process_results.py]
                                                         |
                          +------------------------------+------------------------------+
                          |                              |                              |
                          v                              v                              v
                    data/ (JSON)                  docs/reports/                  [check_alerts.py]
                                                  (markdown)                           |
                          |                              |                              v
                          +---------------+--------------+                       data/alerts.json
                                          |                                              |
                                          v                                              v
                                   [generate_charts.py]                          WeChat + Email
                                          |
                                          v
                                 docs/assets/charts/
                                          |
                                          v
                                     MkDocs build
                                          |
                                          v
                                      GitHub Pages
```

## Repository Structure

```
vllm-omni-kanban/
├── .github/
│   └── workflows/
│       ├── build-dashboard.yml    # Manual rebuild/deploy only
│       └── process-results.yml    # Handles dispatch and scheduled daily refresh
├── data/
│   ├── results/                   # Per-date CI results (sharded for efficiency)
│   │   └── 2026-03-13.json        # One file per day
│   ├── index.json                 # Lightweight index: last_updated, available dates
│   ├── config.json                # Hardware, models, thresholds config
│   └── alerts.json                # Alert history
├── docs/
│   ├── index.md                   # Dashboard homepage
│   ├── reports/
│   │   └── 2026-03-13.md          # Daily report (auto-generated, permanent archive)
│   ├── assets/
│   │   └── charts/                # Generated ECharts JSON data files
│   └── overrides/
│       └── main.html              # MkDocs theme override (injects ECharts JS)
├── scripts/
│   ├── fetch_latest_results.py    # Fetches full daily snapshot from external source
│   ├── process_results.py         # Parse CI data, deduplicate, prune, generate reports
│   ├── generate_charts.py         # Create ECharts JSON data files
│   └── check_alerts.py            # Compare metrics vs thresholds, send notifications
├── mkdocs.yml                     # MkDocs configuration (with macros plugin)
└── requirements.txt               # Python dependencies
```

> **Note on storage sharding:** Results are stored as per-date files (`data/results/YYYY-MM-DD.json`) rather than a single `results.json`. This keeps git diffs small (one file changed per day), prevents unbounded file growth, and allows efficient reads by date range.

## Data Format

### CI Result Schema (Input)

```json
{
  "timestamp": "2025-03-13T06:00:00+08:00",
  "commit": "abc123def456",
  "hardware": "NVIDIA-H100",
  "model": "Qwen3-TTS",
  "metrics": {
    "stability": {
      "pass_rate": 0.95,
      "crash_count": 0,
      "error_types": {"oom": 0, "timeout": 1}
    },
    "performance": {
      "latency_p50_ms": 120,
      "latency_p99_ms": 350,
      "throughput_tokens_per_sec": 1500,
      "ttft_ms": 85
    },
    "accuracy": {
      "benchmark_score": 0.89
    },
    "custom": {
      "real_time_factor": 0.12,
      "audio_quality_mos": 4.2
    }
  }
}
```

### Per-Date File Structure (`data/results/YYYY-MM-DD.json`)

```json
{
  "date": "2026-03-13",
  "results": [
    // array of CI results for this date
  ]
}
```

### Index File (`data/index.json`)

```json
{
  "last_updated": "2026-03-13T06:00:00+08:00",
  "retention_days": 90,
  "dates": ["2026-03-13", "2026-03-12", "..."]
}
```

> **Daily snapshot rule:** `process_results.py` maintains one snapshot per `(date, hardware, model)` tuple. Exact duplicate pushes (for example, a CI retry with the same payload) are ignored with a log warning. The scheduled 6:00 AM fetch is authoritative for the day and may replace an existing snapshot for the same tuple if it contains newer data.

> **90-day pruning:** On each run, `index.json` is updated and date files older than 90 days are deleted. Daily reports in `docs/reports/` are **not** pruned — they serve as a permanent archive.

### Per-Model Metric Registry

The config defines which metrics are required/optional for each model:

```json
{
  "models": {
    "Qwen-image": {
      "display_name": "Qwen Image",
      "category": "image_generation",
      "metrics": {
        "required": ["pass_rate", "latency_p99_ms", "throughput_tokens_per_sec"],
        "optional": ["image_quality_score", "generation_time_ms"]
      },
      "alert_overrides": {}
    },
    "Qwen-image-edit": {
      "display_name": "Qwen Image Edit",
      "category": "image_editing",
      "metrics": {
        "required": ["pass_rate", "latency_p99_ms"],
        "optional": ["edit_quality_score", "generation_time_ms"]
      },
      "alert_overrides": {}
    },
    "WAN2.2": {
      "display_name": "WAN 2.2",
      "category": "video_generation",
      "metrics": {
        "required": ["pass_rate", "latency_p99_ms"],
        "optional": ["video_quality_score", "generation_time_ms"]
      },
      "alert_overrides": {}
    },
    "Qwen3-Omni": {
      "display_name": "Qwen3 Omni",
      "category": "multimodal",
      "metrics": {
        "required": ["pass_rate", "latency_p99_ms", "ttft_ms", "throughput_tokens_per_sec"],
        "optional": ["benchmark_score"]
      },
      "alert_overrides": {}
    },
    "Qwen3-TTS": {
      "display_name": "Qwen3 TTS",
      "category": "audio_synthesis",
      "metrics": {
        "required": ["pass_rate", "latency_p99_ms"],
        "optional": ["real_time_factor", "audio_quality_mos", "speaker_similarity"]
      },
      "alert_overrides": {
        "latency_p99_ms_critical": 2000
      }
    }
  }
}
```

**Extensibility:** New models and metrics can be added by updating `config.json` and including them in CI results. No code changes required. Use `alert_overrides` to set per-model thresholds that differ from global defaults.

## CI/CD Workflow

### Data Push (from vLLM-omni CI)

> **Payload size constraint:** GitHub `repository_dispatch` has a 10KB limit on `client_payload`. Each CI result is ~1–2KB (single model/hardware pair). CI should push **one dispatch per result** rather than batching all results into one payload to stay within limits.

```yaml
# In vLLM-omni repo's CI, after tests complete (one call per model/hardware):
- name: Push results to kanban repo
  run: |
    PAYLOAD=$(python scripts/build_kanban_payload.py)  # builds single result JSON
    curl -X POST \
      -H "Authorization: token ${{ secrets.KANBAN_TOKEN }}" \
      -H "Content-Type: application/json" \
      https://api.github.com/repos/YOUR-ORG/vllm-omni-kanban/dispatches \
      -d "{\"event_type\": \"ci_results\", \"client_payload\": ${PAYLOAD}}"
```

### Scheduled Fetch (from external source)

The scheduled workflow does not depend on `repository_dispatch`. At 6:00 AM Beijing time it fetches a full daily batch from an external JSON source published by the vLLM-omni pipeline, for example an artifact manifest or object-storage URL exposed via `RESULTS_SOURCE_URL`.

```bash
python scripts/fetch_latest_results.py --output /tmp/daily-results.json
# Reads from: RESULTS_SOURCE_URL (+ optional auth token)
# Writes to: batch JSON with 25 daily snapshot results
```

### Process & Deploy (this repo)

The workflow is split into three jobs so failures in alerting or deployment don't block each other, and so errors are surfaced clearly.

```yaml
# .github/workflows/process-results.yml
on:
  repository_dispatch:
    types: [ci_results]
  schedule:
    - cron: '0 22 * * *'  # 6:00 AM Beijing time (UTC+8)

jobs:
  process:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - name: Fetch scheduled batch
        if: github.event_name == 'schedule'
        run: python scripts/fetch_latest_results.py --output /tmp/daily-results.json
        env:
          RESULTS_SOURCE_URL: ${{ secrets.RESULTS_SOURCE_URL }}
          RESULTS_SOURCE_TOKEN: ${{ secrets.RESULTS_SOURCE_TOKEN }}
      - name: Validate input schema
        run: |
          if [ "${{ github.event_name }}" = "schedule" ]; then
            python scripts/process_results.py --validate-only --input /tmp/daily-results.json --source schedule
          else
            python scripts/process_results.py --validate-only --source dispatch
          fi
      - name: Process and store results
        run: |
          if [ "${{ github.event_name }}" = "schedule" ]; then
            python scripts/process_results.py --input /tmp/daily-results.json --source schedule
          else
            python scripts/process_results.py --source dispatch
          fi
      - name: Generate chart data
        run: python scripts/generate_charts.py
      - name: Commit data changes
        run: |
          git config user.name "CI Bot"
          git config user.email "ci-bot@github.com"
          git add data/ docs/reports/ docs/assets/charts/
          git diff --staged --quiet || git commit -m "chore: update results $(date -u +%Y-%m-%d)"
          git push

  alert:
    needs: process
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main  # pull latest after process job committed
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - name: Check thresholds and send alerts
        run: python scripts/check_alerts.py
        env:
          WECHAT_WEBHOOK: ${{ secrets.WECHAT_WEBHOOK }}
          EMAIL_SMTP_HOST: ${{ secrets.EMAIL_SMTP_HOST }}
          EMAIL_SMTP_PORT: ${{ secrets.EMAIL_SMTP_PORT }}
          EMAIL_SMTP_USER: ${{ secrets.EMAIL_SMTP_USER }}
          EMAIL_SMTP_PASS: ${{ secrets.EMAIL_SMTP_PASS }}
          EMAIL_FROM: ${{ secrets.EMAIL_FROM }}
          EMAIL_TO: ${{ secrets.EMAIL_TO }}
      - name: Commit alert history
        run: |
          git config user.name "CI Bot"
          git config user.email "ci-bot@github.com"
          git add data/alerts.json
          git diff --staged --quiet || git commit -m "chore: update alerts $(date -u +%Y-%m-%d)"
          git push

  deploy:
    needs: alert
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
        with:
          ref: main  # pull latest after process + alert jobs committed
      - uses: actions/setup-python@v5
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - name: Build and deploy MkDocs
        run: mkdocs gh-deploy --force
```

## Dashboard Pages

### Homepage (docs/index.md)

| Section | Content |
|---------|---------|
| **Summary Cards** | Overall pass rate, avg latency, latest commit date |
| **Hardware Status Grid** | 5 cards (A100, H100, H20, MI300X, Ascend) with status |
| **Model Performance Table** | 5 rows (models) × 5 columns (hardware) |
| **Trend Charts** | 7-day/30-day trend lines |
| **Recent Alerts** | Last 5 alert events |

### Daily Report Page (docs/reports/YYYY-MM-DD.md)

- Summary with commit, total tests, pass rate
- Per-hardware breakdown with model tables
- Alerts triggered that day
- Trend comparison vs 7-day average

### ECharts Integration

MkDocs renders Markdown to static HTML. ECharts charts are embedded via the `mkdocs-macros` plugin, which allows Jinja2 macros in Markdown files. `generate_charts.py` writes pre-computed ECharts option JSON files to `docs/assets/charts/`, and a macro renders them into `<div>` containers.

**`mkdocs.yml` additions:**
```yaml
theme:
  name: material
  custom_dir: docs/overrides

plugins:
  - macros

extra_javascript:
  - https://cdn.jsdelivr.net/npm/echarts@5/dist/echarts.min.js
  - assets/js/render_charts.js
```

**Macro usage in Markdown (`docs/index.md`):**
```markdown
{{ render_chart("pass_rate_trend_7d") }}
```

**`docs/overrides/main.html`** extends the Material theme to include the ECharts JS bundle and the `render_charts.js` initializer that reads the pre-computed JSON and mounts each chart into its container div.

### Chart Types (ECharts)

- **Line charts** — Time series for pass rate, latency trends (7-day, 30-day)
- **Heatmap** — Model × Hardware matrix (color = pass rate)
- **Bar charts** — Per-metric hardware comparison for a single model

## Alerting Rules

### Absolute Thresholds

| Trigger | Level | Message |
|---------|-------|---------|
| Pass rate < 80% | 🔴 Critical | Stability critical |
| Pass rate < 90% | 🟡 Warning | Stability degraded |
| Latency P99 > 1000ms | 🔴 Critical | Latency spike |
| Crash count ≥ 3 | 🔴 Critical | Multiple crashes |

### Regression Detection (vs 7-day baseline)

| Metric | Regression Threshold |
|--------|---------------------|
| Pass rate | -5% absolute |
| Latency P99 | +20% relative |
| TTFT | +20% relative |
| Throughput | -15% relative |
| Benchmark score | -5% relative |

### Alert Cooldown (Suppression)

To prevent alert fatigue, `check_alerts.py` tracks active alerts in `alerts.json`. An alert for the same `(hardware, model, metric, level)` combination is suppressed for **24 hours** after it was first sent. Once the metric recovers above the threshold, the cooldown is reset.

```json
// alerts.json entry
{
  "id": "h100-qwen3omni-latency_p99-critical",
  "hardware": "NVIDIA-H100",
  "model": "Qwen3-Omni",
  "metric": "latency_p99_ms",
  "level": "critical",
  "first_triggered": "2026-03-13T06:00:00+08:00",
  "last_triggered": "2026-03-13T06:00:00+08:00",
  "suppressed_until": "2026-03-14T06:00:00+08:00",
  "resolved": false
}
```

### Notification Channels

- **WeChat (企业微信)** — Webhook-based
- **Email** — SMTP-based (`EMAIL_SMTP_HOST`, `EMAIL_SMTP_PORT`, `EMAIL_SMTP_USER`, `EMAIL_SMTP_PASS`, `EMAIL_FROM`, `EMAIL_TO`)

### Notification Format

```
[vLLM-Omni Kanban Alert] 🟡 Warning - Regression

Hardware: NVIDIA H100
Model: Qwen3-Omni
Metric: Latency P99
Regression: 280ms → 350ms (+25%)
Baseline: 7-day average

Time: 2025-03-13 06:00:00 CST
Commit: abc123d
Link: https://your-org.github.io/vllm-omni-kanban/
```

## Implementation Phases

### Phase 1: Foundation (Week 1)
- Initialize repo structure with sharded `data/results/` layout
- Set up MkDocs Material theme with macros plugin
- Define and validate JSON schemas (CI result, index, config, alerts)
- Implement `process_results.py` (validate → deduplicate → append → prune)
- Write Phase 1 tests; achieve ≥80% coverage on `process_results.py`
- Implement `fetch_latest_results.py` contract and external source configuration

### Phase 2: Alerting (Week 2)
- Implement `check_alerts.py`: absolute thresholds, regression detection (7-day baseline)
- Add 24-hour alert cooldown / suppression logic
- Handle sparse baseline (< 7 days): skip regression check, log warning
- Integrate WeChat Enterprise webhook notifications
- Integrate Email SMTP notifications
- Write Phase 2 tests; achieve ≥95% coverage on `check_alerts.py`

### Phase 3: Dashboard & Visualization (Week 3)
- Build homepage (`docs/index.md`) with summary cards, hardware grid, model matrix
- Implement daily report generator (auto-creates `docs/reports/YYYY-MM-DD.md`)
- Implement `generate_charts.py` (ECharts JSON output for line, heatmap, bar)
- Wire ECharts via MkDocs macros + `docs/overrides/main.html`
- Write Phase 3 tests; achieve ≥80% coverage on `generate_charts.py`

### Phase 4: CI Integration (Week 4)
- Create split `process-results.yml` workflow (process / alert / deploy jobs)
- Add `repository_dispatch` handler with schema validation step
- Configure scheduled fetch job (6:00 AM Beijing = UTC 22:00)
- Ensure generated charts and `alerts.json` are committed before deployment
- Test end-to-end with sample data using `act` or manual dispatch

### Phase 5: Polish & Docs (Week 5)
- Add MkDocs navigation, search, report archive index
- Write contributor guide: how to add a new model, new metric, new hardware
- Document secrets setup in GitHub repository settings, including external fetch and email delivery config
- Final end-to-end smoke test with all 5 models × 5 hardware
