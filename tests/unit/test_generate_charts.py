from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

from scripts.generate_charts import build_qwen3_omni_history_payload, parse_qwen3_omni_filename


def test_parse_qwen3_omni_filename_supports_expected_layout() -> None:
    parsed = parse_qwen3_omni_filename(Path("result_test_qwen3_omni_chunk_random_4_40_20260310-182556.json"))
    assert parsed == {
        "test_name": "qwen3_omni_chunk",
        "dataset_name": "random",
        "max_concurrency": 4,
        "num_prompts": 40,
        "timestamp_key": "20260310-182556",
        "sort_timestamp": "2026-03-10T18:25:56",
        "date": "2026-03-10 18:25:56",
    }


def test_qwen3_omni_history_groups_and_sorts_by_config_and_time(repo_root: Path, tmp_path: Path) -> None:
    source_dir = tmp_path / "qwen3omni"
    source_dir.mkdir()
    first = {
        "date": "20260308-181548",
        "endpoint_type": "openai-chat-omni",
        "backend": "openai-chat-omni",
        "model_id": "Qwen/Qwen3-Omni-30B-A3B-Instruct",
        "tokenizer_id": "Qwen/Qwen3-Omni-30B-A3B-Instruct",
        "request_throughput": 0.12,
        "output_throughput": 12.2,
        "total_token_throughput": 24.4,
        "mean_ttft_ms": 60.5,
        "p99_ttft_ms": 222.1,
        "mean_e2el_ms": 8188.9,
    }
    second = dict(first)
    second["mean_ttft_ms"] = 58.1
    third = dict(first)
    third["mean_ttft_ms"] = 80.4
    third["max_concurrency"] = 4
    third["num_prompts"] = 40

    (source_dir / "result_test_qwen3_omni_random_1_10_20260308-181548.json").write_text(json.dumps(first), encoding="utf-8")
    (source_dir / "result_test_qwen3_omni_random_1_10_20260309-181745.json").write_text(json.dumps(second), encoding="utf-8")
    (source_dir / "result_test_qwen3_omni_random_4_40_20260310-181940.json").write_text(json.dumps(third), encoding="utf-8")

    config = json.loads((repo_root / "data" / "config.json").read_text(encoding="utf-8"))
    payload = build_qwen3_omni_history_payload(config, source_dir)

    assert payload["record_count"] == 3
    assert payload["group_count"] == 2
    assert [item["source_file"] for item in payload["records"]] == [
        "result_test_qwen3_omni_random_1_10_20260309-181745.json",
        "result_test_qwen3_omni_random_1_10_20260308-181548.json",
        "result_test_qwen3_omni_random_4_40_20260310-181940.json",
    ]
    assert payload["groups"][0]["record_count"] == 2
    assert [item["date"] for item in payload["groups"][0]["records"]] == [
        "2026-03-09 18:17:45",
        "2026-03-08 18:15:48",
    ]


def test_output_files_created(repo_root: Path) -> None:
    result = subprocess.run(
        [sys.executable, "scripts/generate_charts.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert (repo_root / "docs" / "assets" / "charts" / "pass_rate_trend_1d.json").exists()
    assert (repo_root / "docs" / "assets" / "charts" / "pass_rate_trend_7d.json").exists()
    assert (repo_root / "docs" / "assets" / "charts" / "pass_rate_trend_30d.json").exists()
    assert (repo_root / "docs" / "assets" / "charts" / "qwen3_omni_throughput_tokens_per_sec_1d.json").exists()
    assert (repo_root / "docs" / "assets" / "charts" / "qwen3_omni_throughput_tokens_per_sec_7d.json").exists()
    assert (repo_root / "docs" / "assets" / "charts" / "qwen3_omni_throughput_tokens_per_sec_30d.json").exists()
    assert (repo_root / "docs" / "assets" / "charts" / "qwen3_omni_tpot_ms_7d.json").exists()
    assert (repo_root / "docs" / "assets" / "charts" / "qwen3_omni_history.json").exists()
    assert (repo_root / "docs" / "assets" / "charts" / "qwen3_tts_real_time_factor_7d.json").exists()
    assert (repo_root / "docs" / "assets" / "charts" / "qwen_image_e2e_latency_ms_7d.json").exists()
    assert (repo_root / "docs" / "assets" / "charts" / "wan22_peak_memory_gb_7d.json").exists()
