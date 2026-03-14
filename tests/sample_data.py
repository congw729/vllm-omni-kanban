from __future__ import annotations

import hashlib
import json
import random


MODELS = ["Qwen-image", "Qwen-Image-edit", "WAN2.2", "Qwen3-Omni", "Qwen3-TTS"]
HARDWARE = ["NVIDIA-A100", "NVIDIA-H100", "NVIDIA-H20", "AMD-MI300X", "Ascend-A2", "Ascend-A3"]


def stable_rng(*parts: str) -> random.Random:
    seed_source = "|".join(parts).encode("utf-8")
    seed = int(hashlib.sha256(seed_source).hexdigest()[:16], 16)
    return random.Random(seed)


def make_result(date_str: str, model: str, hardware: str, base: dict) -> dict:
    item = json.loads(json.dumps(base))
    rng = stable_rng(date_str, model, hardware)
    item["timestamp"] = f"{date_str}T06:00:00+08:00"
    item["commit"] = hashlib.sha256(f"{date_str}-{model}".encode("utf-8")).hexdigest()[:12]
    item["model"] = model
    item["hardware"] = hardware

    pass_rate = round(0.88 + rng.random() * 0.11, 4)
    latency_p99 = round(180 + rng.random() * 520, 2)
    latency_p50 = round(latency_p99 * (0.28 + rng.random() * 0.16), 2)
    throughput = round(900 + rng.random() * 900, 2)
    ttft = round(45 + rng.random() * 120, 2)
    benchmark_score = round(0.72 + rng.random() * 0.24, 4)
    crash_count = 1 if pass_rate < 0.9 and rng.random() < 0.18 else 0

    item["metrics"]["stability"]["pass_rate"] = pass_rate
    item["metrics"]["stability"]["crash_count"] = crash_count
    item["metrics"]["stability"]["error_types"] = {"timeout": crash_count, "oom": 1 if crash_count and rng.random() < 0.3 else 0}
    item["metrics"]["performance"]["latency_p99_ms"] = latency_p99
    item["metrics"]["performance"]["latency_p50_ms"] = latency_p50
    item["metrics"]["performance"]["throughput_tokens_per_sec"] = throughput
    item["metrics"]["performance"]["ttft_ms"] = ttft
    item["metrics"]["accuracy"]["benchmark_score"] = benchmark_score
    item["metrics"]["custom"]["audio_quality_mos"] = round(3.8 + rng.random() * 0.9, 2)
    return item


def build_batch_for_date(date_str: str, base: dict) -> dict:
    return {"results": [make_result(date_str, model, hardware, base) for model in MODELS for hardware in HARDWARE]}
