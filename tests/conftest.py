from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


@pytest.fixture
def sample_ci_result() -> dict:
    return {
        "timestamp": "2026-03-14T06:00:00+08:00",
        "commit": "abc123def456",
        "hardware": "NVIDIA-H100",
        "model": "Qwen3-TTS",
        "metrics": {
            "stability": {"pass_rate": 0.95, "crash_count": 0, "error_types": {"timeout": 0}},
            "performance": {
                "latency_p99_ms": 350,
                "latency_p50_ms": 120,
                "throughput_tokens_per_sec": 1500,
                "ttft_ms": 85
            },
            "accuracy": {"benchmark_score": 0.89},
            "custom": {"audio_quality_mos": 4.2},
        },
    }


@pytest.fixture
def sample_daily_batch(sample_ci_result: dict) -> dict:
    models = ["Qwen-image", "Qwen-Image-edit", "WAN2.2", "Qwen3-Omni", "Qwen3-TTS"]
    hardware = ["NVIDIA-A100", "NVIDIA-H100", "NVIDIA-H20", "AMD-MI300X", "Ascend-A2A3"]
    results = []
    for model in models:
        for hw in hardware:
            item = json.loads(json.dumps(sample_ci_result))
            item["model"] = model
            item["hardware"] = hw
            results.append(item)
    return {"results": results}


@pytest.fixture
def repo_root() -> Path:
    return ROOT
