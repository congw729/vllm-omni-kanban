# vLLM-Omni Kanban Design Document

**Date:** 2025-03-13
**Status:** Approved
**Author:** Design brainstorming session

## Overview

vLLM-Omni Kanban is a monitoring dashboard that tracks stability, performance, and accuracy of vLLM multimodal models across different hardware platforms. It updates daily at 6:00 AM Beijing time using data from vLLM-omni CI.

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

### Approach: Simple Push-Based Pipeline

```
vLLM-omni CI --(push)--> vllm-omni-kanban repo
                              |
                              v
                        [process_results.py]
                              |
              +---------------+---------------+
              |               |               |
              v               v               v
        data/          docs/reports/    [check_alerts.py]
        (JSON)          (markdown)            |
                              |               v
                              v         WeChat + Email
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
│       ├── build-dashboard.yml    # Build & deploy MkDocs to GitHub Pages
│       └── process-results.yml    # Triggered when new results arrive
├── data/
│   ├── results.json               # All CI results (90-day rolling)
│   ├── config.json                # Hardware, models, thresholds config
│   └── alerts.json                # Alert history
├── docs/
│   ├── index.md                   # Dashboard homepage
│   ├── reports/
│   │   └── 2025-03-13.md          # Daily report (auto-generated)
│   ├── assets/
│   │   └── charts/                # Generated chart data/HTML
│   └── overrides/                 # MkDocs customizations
├── scripts/
│   ├── process_results.py         # Parse CI data, generate reports
│   ├── generate_charts.py         # Create chart data for ECharts
│   └── check_alerts.py            # Compare metrics vs thresholds
├── mkdocs.yml                     # MkDocs configuration
└── requirements.txt               # Python dependencies
```

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

### Aggregated results.json Structure

```json
{
  "last_updated": "2025-03-13T06:00:00+08:00",
  "retention_days": 90,
  "results": [
    // array of CI results, pruned to 90 days
  ]
}
```

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
      }
    },
    "Qwen3-TTS": {
      "display_name": "Qwen3 TTS",
      "category": "audio_synthesis",
      "metrics": {
        "required": ["pass_rate", "latency_p99_ms"],
        "optional": ["real_time_factor", "audio_quality_mos", "speaker_similarity"]
      }
    }
    // ... other models
  }
}
```

**Extensibility:** New models and metrics can be added by updating config.json and including them in CI results. No code changes required.

## CI/CD Workflow

### Data Push (from vLLM-omni CI)

```yaml
# In vLLM-omni repo's CI, after tests complete:
- name: Push results to kanban repo
  run: |
    curl -X POST \
      -H "Authorization: token ${{ secrets.KANBAN_TOKEN }}" \
      -H "Content-Type: application/json" \
      https://api.github.com/repos/YOUR-ORG/vllm-omni-kanban/dispatches \
      -d '{"event_type": "ci_results", "client_payload": {...}}'
```

### Process & Deploy (this repo)

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
      - run: python scripts/process_results.py
      - run: python scripts/generate_charts.py
      - run: python scripts/check_alerts.py
        env:
          WECHAT_WEBHOOK: ${{ secrets.WECHAT_WEBHOOK }}
          EMAIL_SMTP: ${{ secrets.EMAIL_SMTP }}
      - run: |
          git config user.name "CI Bot"
          git add data/ docs/
          git diff --quiet && git diff --staged --quiet || git commit -m "chore: update results"
          git push
      - run: mkdocs gh-deploy --force
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

### Chart Types (ECharts)

- **Line charts** — Time series for trends
- **Heatmap** — Model × Hardware matrix
- **Bar charts** — Hardware comparison for single model

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

### Notification Channels

- **WeChat (企业微信)** — Webhook-based
- **Email** — SMTP-based

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
- Initialize repo structure
- Set up MkDocs with Material theme
- Define JSON schema for CI results
- Implement `process_results.py` (append + prune logic)
- Set up GitHub Pages deployment

### Phase 2: Dashboard & Visualization (Week 2)
- Build homepage with summary cards and tables
- Implement daily report generator
- Add ECharts integration (line charts, heatmap)
- Create `generate_charts.py`

### Phase 3: CI Integration (Week 3)
- Create `process-results.yml` workflow
- Add `repository_dispatch` handler
- Configure scheduled backup job (6:00 AM Beijing)
- Test end-to-end with sample data

### Phase 4: Alerting (Week 4)
- Implement `check_alerts.py` with threshold logic
- Add regression detection (7-day baseline)
- Integrate WeChat webhook notifications
- Integrate Email SMTP notifications
- Add `alerts.json` logging

### Phase 5: Polish & Docs (Week 5)
- Add navigation, search, filtering
- Write user documentation
- Add contributor guide for extending metrics
- Configure secrets in GitHub settings
