from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_validate_only_flag(repo_root: Path, sample_ci_result: dict, tmp_path: Path) -> None:
    input_path = tmp_path / "input.json"
    input_path.write_text(json.dumps(sample_ci_result), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/process_results.py", "--validate-only", "--input", str(input_path)],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    assert "validated 1 results" in result.stdout


def test_process_batch_input(repo_root: Path, sample_daily_batch: dict, tmp_path: Path) -> None:
    input_path = tmp_path / "batch.json"
    input_path.write_text(json.dumps(sample_daily_batch), encoding="utf-8")
    result = subprocess.run(
        [sys.executable, "scripts/process_results.py", "--input", str(input_path), "--source", "schedule"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0
    day_file = repo_root / "data" / "results" / "2026-03-14.json"
    assert day_file.exists()


def test_scheduled_fetch_replaces_same_day_snapshot(repo_root: Path, sample_ci_result: dict, tmp_path: Path) -> None:
    first = dict(sample_ci_result)
    second = json.loads(json.dumps(sample_ci_result))
    second["commit"] = "updatedcommit123"
    second["timestamp"] = "2026-03-14T07:00:00+08:00"
    second["metrics"]["performance"]["latency_p99_ms"] = 420

    first_path = tmp_path / "first.json"
    second_path = tmp_path / "second.json"
    first_path.write_text(json.dumps(first), encoding="utf-8")
    second_path.write_text(json.dumps(second), encoding="utf-8")

    subprocess.run(
        [sys.executable, "scripts/process_results.py", "--input", str(first_path), "--source", "dispatch"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    subprocess.run(
        [sys.executable, "scripts/process_results.py", "--input", str(second_path), "--source", "schedule"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    day_file = repo_root / "data" / "results" / "2026-03-14.json"
    payload = json.loads(day_file.read_text(encoding="utf-8"))
    match = next(item for item in payload["results"] if item["hardware"] == "NVIDIA-H100" and item["model"] == "Qwen3-TTS")
    assert match["commit"] == "updatedcommit123"
