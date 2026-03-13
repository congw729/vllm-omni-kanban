# vLLM-Omni Kanban

Monitoring dashboard for vLLM multimodal model stability, performance, and accuracy across hardware platforms. Tracks daily CI results with 90-day retention and alerting.

## Features

- **Models:** Qwen-image, Qwen-Image-edit, WAN2.2, Qwen3-Omni, Qwen3-TTS
- **Hardware:** NVIDIA A100/H100/H20, AMD MI300X, Ascend NPU A2/A3
- **Metrics:** Pass rate, latency (p50/p99), throughput, TTFT, benchmark scores
- **90-day rolling retention**, daily Markdown reports, alerts (absolute + regression), WeChat & Email notifications

## Quick Start

```bash
pip install -r requirements.txt
pytest
```

**Process results:** `scripts/process_results.py` — append, prune, generate daily report  
**Alerts:** `scripts/check_alerts.py` — thresholds and 7-day regression  
**Charts:** `scripts/generate_charts.py` — line charts, heatmaps

## Docs

- [PRD](docs/plans/2026-03-13-prd.md)
- [Kanban Design](docs/plans/2025-03-13-kanban-design.md)
- [TDD Plan](docs/plans/2025-03-13-tdd-plan-design.md)
- [Implementation Plan](docs/plans/2026-03-13-implementation-plan.md)

## License

Apache-2.0
