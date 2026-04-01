#!/usr/bin/env python3
"""Merge downloaded nightly perf JSON files into data/results/YYYY-MM-DD.json.

Appends kanban-shaped entries (see KANBAN_dev.md: timestamp, commit, model, metrics).
Dedupes by (commit, source_file, entry_index).
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

PERF_METRIC_KEYS = frozenset(
    {
        "request_throughput",
        "output_throughput",
        "total_token_throughput",
        "mean_ttft_ms",
        "median_ttft_ms",
        "p99_ttft_ms",
        "mean_tpot_ms",
        "median_tpot_ms",
        "p99_tpot_ms",
        "mean_itl_ms",
        "median_itl_ms",
        "p99_itl_ms",
        "mean_e2el_ms",
        "median_e2el_ms",
        "p99_e2el_ms",
        "mean_audio_rtf",
        "median_audio_rtf",
        "p99_audio_rtf",
        "mean_audio_ttfp_ms",
        "median_audio_ttfp_ms",
        "p99_audio_ttfp_ms",
        "mean_audio_duration_s",
        "median_audio_duration_s",
        "p99_audio_duration_s",
        "throughput_qps",
        "latency_mean",
        "latency_median",
        "latency_p99",
        "latency_p50",
    },
)


def _parse_omni_timestamp(date_val: str | None) -> str:
    if not date_val or len(date_val) < 15:
        return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    # YYYYMMDD-HHMMSS
    d, t = date_val.split("-", 1)
    return f"{d[:4]}-{d[4:6]}-{d[6:8]}T{t[:2]}:{t[2:4]}:{t[4:6]}Z"


def _pick_performance_metrics(raw: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in raw.items():
        if k in PERF_METRIC_KEYS:
            out[k] = v
    return out


def entries_from_file(
    path: Path,
    *,
    commit: str,
    build_url: str,
    build_number: str,
) -> list[dict[str, Any]]:
    name = path.name
    raw_text = path.read_text(encoding="utf-8")
    data = json.loads(raw_text)
    out: list[dict[str, Any]] = []

    if name.startswith("result_test_") and isinstance(data, dict):
        ts = _parse_omni_timestamp(data.get("date"))
        model = data.get("model_id") or data.get("model") or "unknown"
        entry = {
            "timestamp": ts,
            "commit": commit,
            "build_url": build_url,
            "build_number": build_number,
            "hardware": None,
            "model": model,
            "source": "buildkite_nightly_perf",
            "artifact_kind": "omni_result_test",
            "source_file": name,
            "metrics": {
                "performance": _pick_performance_metrics(data),
                "raw_omni": data,
            },
        }
        out.append(entry)
        return out

    if name.startswith("benchmark_results_"):
        rows: list[dict[str, Any]]
        if isinstance(data, list):
            rows = data
        elif isinstance(data, dict) and isinstance(data.get("results"), list):
            rows = data["results"]
        else:
            rows = [data] if isinstance(data, dict) else []

        for idx, row in enumerate(rows):
            if not isinstance(row, dict):
                continue
            model = row.get("model") or row.get("model_id") or "unknown"
            ts = row.get("timestamp") or row.get("date") or _parse_omni_timestamp(None)
            if isinstance(ts, str) and len(ts) == 15 and ts[8] == "-":
                ts = _parse_omni_timestamp(ts)
            elif not isinstance(ts, str) or "T" not in ts:
                ts = _parse_omni_timestamp(None)
            entry = {
                "timestamp": ts,
                "commit": commit,
                "build_url": build_url,
                "build_number": build_number,
                "hardware": None,
                "model": model,
                "source": "buildkite_nightly_perf",
                "artifact_kind": "diffusion_benchmark_results",
                "source_file": name,
                "entry_index": idx,
                "metrics": {
                    "performance": _pick_performance_metrics(row),
                    "raw_diffusion_row": row,
                },
            }
            out.append(entry)
        return out

    return []


def dedupe_key(e: dict[str, Any]) -> tuple:
    return (
        e.get("commit") or "",
        e.get("source_file") or "",
        e.get("artifact_kind") or "",
        e.get("entry_index", 0),
    )


def load_results_list(results_path: Path) -> list[dict[str, Any]]:
    if not results_path.exists():
        return []
    try:
        data = json.loads(results_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []
    if isinstance(data, list):
        return [x for x in data if isinstance(x, dict)]
    return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest perf JSON files into data/results daily file.")
    parser.add_argument("--input-dir", required=True, help="Directory with downloaded *.json")
    parser.add_argument(
        "--date",
        default=None,
        help="UTC calendar date YYYY-MM-DD for output file (default: today UTC)",
    )
    parser.add_argument(
        "--data-root",
        default="data/results",
        help="Root directory for daily JSON files",
    )
    parser.add_argument("--commit", default="", help="Git commit from Buildkite")
    parser.add_argument("--build-url", default="", help="Build URL")
    parser.add_argument("--build-number", default="", help="Build number")
    args = parser.parse_args()

    day = args.date or datetime.now(timezone.utc).strftime("%Y-%m-%d")
    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        sys.stderr.write(f"input-dir is not a directory: {input_dir}\n")
        sys.exit(1)

    results_path = Path(args.data_root) / f"{day}.json"
    results_path.parent.mkdir(parents=True, exist_ok=True)

    existing = load_results_list(results_path)
    keys_existing = {dedupe_key(e) for e in existing}
    new_entries: list[dict[str, Any]] = []

    for path in sorted(input_dir.rglob("*.json")):
        if not path.is_file():
            continue
        if not (
            path.name.startswith("result_test_") or path.name.startswith("benchmark_results_")
        ):
            continue
        for entry in entries_from_file(
            path,
            commit=args.commit,
            build_url=args.build_url,
            build_number=args.build_number,
        ):
            k = dedupe_key(entry)
            if k in keys_existing:
                continue
            keys_existing.add(k)
            new_entries.append(entry)

    merged = existing + new_entries
    results_path.write_text(json.dumps(merged, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {results_path} ({len(new_entries)} new, {len(merged)} total entries).")


if __name__ == "__main__":
    main()
