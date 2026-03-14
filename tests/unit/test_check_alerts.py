from __future__ import annotations

import json
import subprocess
import sys

from scripts.check_alerts import check_absolute_thresholds
from tests.sample_data import HARDWARE, MODELS, build_batch_for_date


def test_absolute_pass_rate_warning(sample_ci_result: dict, repo_root) -> None:
    sample_ci_result["metrics"]["stability"]["pass_rate"] = 0.85
    from scripts.process_results import load_json

    config = load_json(repo_root / "data" / "config.json", {})
    alerts = check_absolute_thresholds(sample_ci_result, config)
    assert any(alert["metric"] == "pass_rate" for alert in alerts)


def test_regression_alert_written(repo_root, sample_daily_batch: dict, tmp_path, monkeypatch) -> None:
    from scripts.check_alerts import load_json as load_alert_json

    historical_dates = [
        "2026-03-07",
        "2026-03-08",
        "2026-03-09",
        "2026-03-10",
        "2026-03-11",
        "2026-03-12",
        "2026-03-13",
    ]
    for date_str in historical_dates:
        batch = build_batch_for_date(date_str, sample_daily_batch["results"][0])
        for item in batch["results"]:
            item["metrics"]["performance"]["latency_p99_ms"] = 100
        path = tmp_path / f"{date_str}.json"
        path.write_text(json.dumps(batch), encoding="utf-8")

    for date_str in historical_dates:
        subprocess.run(
            [sys.executable, "scripts/process_results.py", "--input", str(tmp_path / f"{date_str}.json"), "--source", "schedule"],
            cwd=repo_root,
            capture_output=True,
            text=True,
            check=False,
        )

    latest = build_batch_for_date("2026-03-14", sample_daily_batch["results"][0])
    for item in latest["results"]:
        item["metrics"]["performance"]["latency_p99_ms"] += 150
    latest_path = tmp_path / "latest.json"
    latest_path.write_text(json.dumps(latest), encoding="utf-8")

    subprocess.run(
        [sys.executable, "scripts/process_results.py", "--input", str(latest_path), "--source", "schedule"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    monkeypatch.delenv("WECHAT_WEBHOOK", raising=False)
    monkeypatch.delenv("EMAIL_SMTP_HOST", raising=False)
    subprocess.run(
        [sys.executable, "scripts/check_alerts.py"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )

    alerts = load_alert_json(repo_root / "data" / "alerts.json", {"alerts": []})
    assert any(alert.get("kind") == "regression" for alert in alerts["alerts"])
