"""Tests for ingest (filesystem + JSON only)."""

import json
import tempfile
from pathlib import Path

import pytest

from scripts.ingest_nightly_perf_json import dedupe_key, entries_from_file, load_results_list


def test_entries_from_omni_result_test(tmp_path: Path) -> None:
    p = tmp_path / "result_test_qwen3_omni_random_1_10_20260308-182108.json"
    p.write_text(
        json.dumps(
            {
                "date": "20260308-182215",
                "model_id": "Qwen/Qwen3-Omni-30B-A3B-Instruct",
                "output_throughput": 1.23,
            }
        ),
        encoding="utf-8",
    )
    entries = entries_from_file(
        p,
        commit="abc",
        build_url="https://buildkite.com/build",
        build_number="42",
    )
    assert len(entries) == 1
    assert entries[0]["model"] == "Qwen/Qwen3-Omni-30B-A3B-Instruct"
    assert entries[0]["artifact_kind"] == "omni_result_test"
    assert entries[0]["metrics"]["performance"]["output_throughput"] == 1.23


def test_entries_from_benchmark_results_list(tmp_path: Path) -> None:
    p = tmp_path / "benchmark_results_test_stem_20260311-053632.json"
    p.write_text(
        json.dumps(
            [
                {"model": "Qwen/Qwen-Image", "throughput_qps": 2.5},
                {"model_id": "Other", "latency_mean": 10.0},
            ]
        ),
        encoding="utf-8",
    )
    entries = entries_from_file(
        p,
        commit="def",
        build_url="",
        build_number="99",
    )
    assert len(entries) == 2
    assert entries[0]["entry_index"] == 0
    assert entries[0]["metrics"]["performance"]["throughput_qps"] == 2.5
    assert entries[1]["model"] == "Other"


def test_dedupe_key_stable() -> None:
    e = {
        "commit": "a",
        "source_file": "f.json",
        "artifact_kind": "omni_result_test",
        "entry_index": 0,
    }
    assert dedupe_key(e) == ("a", "f.json", "omni_result_test", 0)


def test_load_results_list_empty(tmp_path: Path) -> None:
    assert load_results_list(tmp_path / "missing.json") == []


def test_ingest_script_cli_smoke(tmp_path: Path) -> None:
    """Run ingest_nightly_perf_json main via subprocess-style file layout."""
    raw_dir = tmp_path / "raw"
    raw_dir.mkdir()
    (raw_dir / "result_test_x.json").write_text(
        json.dumps({"date": "20260308-182215", "model_id": "M1", "mean_ttft_ms": 5.0}),
        encoding="utf-8",
    )
    out_root = tmp_path / "data" / "results"
    out_root.mkdir(parents=True)
    day_file = out_root / "2026-03-30.json"
    day_file.write_text("[]\n", encoding="utf-8")

    import subprocess
    import sys

    repo_root = Path(__file__).resolve().parents[1]
    ingest = repo_root / "scripts" / "ingest_nightly_perf_json.py"
    r = subprocess.run(
        [
            sys.executable,
            str(ingest),
            "--input-dir",
            str(raw_dir),
            "--date",
            "2026-03-30",
            "--data-root",
            str(tmp_path / "data" / "results"),
            "--commit",
            "c1",
            "--build-number",
            "7",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert r.returncode == 0, r.stderr
    data = json.loads(day_file.read_text(encoding="utf-8"))
    assert len(data) >= 1
    assert data[0]["model"] == "M1"
