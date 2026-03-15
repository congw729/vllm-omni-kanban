from __future__ import annotations

import os
import smtplib
import sys
import logging
from datetime import datetime, timedelta
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import requests

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.common import flatten_metrics, load_json, parse_timestamp, save_json

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

DATA_DIR = ROOT / "data"
RESULTS_DIR = DATA_DIR / "results"
INDEX_PATH = DATA_DIR / "index.json"
CONFIG_PATH = DATA_DIR / "config.json"
ALERTS_PATH = DATA_DIR / "alerts.json"

def alert_id(result: dict[str, Any], metric: str, level: str, kind: str) -> str:
    raw = f"{result['hardware']}-{result['model']}-{metric}-{level}-{kind}"
    return raw.lower().replace(".", "").replace("/", "-")


def check_absolute_thresholds(result: dict[str, Any], config: dict[str, Any]) -> list[dict[str, Any]]:
    flat = flatten_metrics(result["metrics"])
    thresholds = config["thresholds"]
    overrides = config["models"][result["model"]].get("alert_overrides", {})
    alerts = []

    pass_rate = flat.get("pass_rate")
    if isinstance(pass_rate, (int, float)):
        if pass_rate < thresholds["pass_rate_critical"]:
            alerts.append({"metric": "pass_rate", "level": "critical", "value": pass_rate, "kind": "absolute"})
        elif pass_rate < thresholds["pass_rate_warning"]:
            alerts.append({"metric": "pass_rate", "level": "warning", "value": pass_rate, "kind": "absolute"})

    latency_threshold = overrides.get("latency_p99_ms_critical", thresholds["latency_p99_ms_critical"])
    latency = flat.get("latency_p99_ms")
    if isinstance(latency, (int, float)) and latency > latency_threshold:
        alerts.append({"metric": "latency_p99_ms", "level": "critical", "value": latency, "kind": "absolute"})

    crash_count = flat.get("crash_count")
    if isinstance(crash_count, (int, float)) and crash_count >= thresholds["crash_count_critical"]:
        alerts.append({"metric": "crash_count", "level": "critical", "value": crash_count, "kind": "absolute"})

    return alerts


def compute_baseline(index: dict[str, Any], latest_date: str) -> dict[tuple[str, str], dict[str, float]]:
    baseline_dates = [date for date in sorted(index["dates"]) if date < latest_date][-7:]
    aggregates: dict[tuple[str, str], dict[str, list[float]]] = {}

    for date_str in baseline_dates:
        results = load_json(RESULTS_DIR / f"{date_str}.json", {"results": []}).get("results", [])
        for result in results:
            key = (result["hardware"], result["model"])
            flat = flatten_metrics(result["metrics"])
            bucket = aggregates.setdefault(key, {})
            for metric, value in flat.items():
                if isinstance(value, (int, float)):
                    bucket.setdefault(metric, []).append(float(value))

    return {
        key: {metric: sum(values) / len(values) for metric, values in metrics.items() if len(values) >= len(baseline_dates)}
        for key, metrics in aggregates.items()
    } if len(baseline_dates) >= 7 else {}


def check_regressions(result: dict[str, Any], baseline: dict[str, float], config: dict[str, Any]) -> list[dict[str, Any]]:
    if not baseline:
        return []
    flat = flatten_metrics(result["metrics"])
    thresholds = config["thresholds"]["regressions"]
    alerts = []

    checks = [
        ("pass_rate", "warning", baseline.get("pass_rate"), flat.get("pass_rate"), -thresholds["pass_rate_drop"]),
        ("latency_p99_ms", "warning", baseline.get("latency_p99_ms"), flat.get("latency_p99_ms"), thresholds["latency_p99_increase"]),
        ("ttft_ms", "warning", baseline.get("ttft_ms"), flat.get("ttft_ms"), thresholds["ttft_increase"]),
        (
            "throughput_tokens_per_sec",
            "warning",
            baseline.get("throughput_tokens_per_sec"),
            flat.get("throughput_tokens_per_sec"),
            -thresholds["throughput_drop"],
        ),
        (
            "benchmark_score",
            "warning",
            baseline.get("benchmark_score"),
            flat.get("benchmark_score"),
            -thresholds["benchmark_score_drop"],
        ),
    ]

    for metric, level, base_value, current_value, threshold in checks:
        if not isinstance(base_value, (int, float)) or not isinstance(current_value, (int, float)) or base_value == 0:
            continue
        delta = (current_value - base_value) / base_value
        if threshold < 0 and delta <= threshold:
            alerts.append(
                {
                    "metric": metric,
                    "level": level,
                    "value": current_value,
                    "baseline": round(base_value, 4),
                    "delta": round(delta, 4),
                    "kind": "regression",
                }
            )
        elif threshold > 0 and delta >= threshold:
            alerts.append(
                {
                    "metric": metric,
                    "level": level,
                    "value": current_value,
                    "baseline": round(base_value, 4),
                    "delta": round(delta, 4),
                    "kind": "regression",
                }
            )
    return alerts


def format_alert_message(result: dict[str, Any], alert: dict[str, Any]) -> str:
    if alert["kind"] == "regression":
        return (
            f"[vLLM-Omni Kanban Alert] {alert['level'].upper()} - Regression\n\n"
            f"Hardware: {result['hardware']}\n"
            f"Model: {result['model']}\n"
            f"Metric: {alert['metric']}\n"
            f"Current: {alert['value']}\n"
            f"Baseline: {alert['baseline']}\n"
            f"Delta: {alert['delta'] * 100:.2f}%\n"
            f"Time: {result['timestamp']}\n"
            f"Commit: {result['commit']}\n"
        )
    return (
        f"[vLLM-Omni Kanban Alert] {alert['level'].upper()} - Threshold\n\n"
        f"Hardware: {result['hardware']}\n"
        f"Model: {result['model']}\n"
        f"Metric: {alert['metric']}\n"
        f"Value: {alert['value']}\n"
        f"Time: {result['timestamp']}\n"
        f"Commit: {result['commit']}\n"
    )


def send_wechat(message: str, webhook_url: str | None) -> None:
    if not webhook_url:
        return
    response = requests.post(webhook_url, json={"msgtype": "text", "text": {"content": message}}, timeout=10)
    response.raise_for_status()


def send_email(message: str) -> None:
    host = os.getenv("EMAIL_SMTP_HOST")
    port = int(os.getenv("EMAIL_SMTP_PORT", "587"))
    user = os.getenv("EMAIL_SMTP_USER")
    password = os.getenv("EMAIL_SMTP_PASS")
    sender = os.getenv("EMAIL_FROM")
    recipients = os.getenv("EMAIL_TO")
    if not all((host, user, password, sender, recipients)):
        return

    email = EmailMessage()
    email["Subject"] = "vLLM-Omni Kanban Alert"
    email["From"] = sender
    email["To"] = recipients
    email.set_content(message)
    with smtplib.SMTP(host, port) as smtp:
        smtp.starttls()
        smtp.login(user, password)
        smtp.send_message(email)


def within_cooldown(existing: dict[str, Any], now: datetime) -> bool:
    suppressed_until = existing.get("suppressed_until")
    return bool(suppressed_until and datetime.fromisoformat(suppressed_until) > now and not existing.get("resolved"))


def resolve_cleared_alerts(alerts_by_id: dict[str, dict[str, Any]], active_ids: set[str], latest_timestamp: str) -> None:
    for alert in alerts_by_id.values():
        if alert["id"] not in active_ids and not alert.get("resolved"):
            alert.update({"resolved": True, "resolved_at": latest_timestamp})


def check_data_freshness(index: dict[str, Any], freshness_threshold_hours: int = 26) -> dict[str, Any] | None:
    """Check if data is stale (> freshness_threshold_hours old).
    
    Args:
        index: Index data containing last_updated timestamp
        freshness_threshold_hours: Maximum age in hours before alert (default: 26)
        
    Returns:
        Alert dict if data is stale, None otherwise
    """
    if not index.get("last_updated"):
        logger.warning("No last_updated timestamp in index")
        return None
    
    last_update_str = index["last_updated"]
    try:
        last_updated = parse_timestamp(last_update_str)
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid timestamp format: {last_update_str}, error: {e}")
        return None
    
    now = datetime.utcnow()
    age_hours = (now - last_updated).total_seconds() / 3600
    
    if age_hours > freshness_threshold_hours:
        logger.warning(f"Data stale: last update was {age_hours:.1f} hours ago (threshold: {freshness_threshold_hours}h)")
        return {
            "metric": "data_freshness",
            "level": "warning",
            "value": round(age_hours, 2),
            "kind": "absolute",
            "message": f"Data is {age_hours:.1f} hours old (threshold: {freshness_threshold_hours}h)",
        }
    
    logger.info(f"Data fresh: last update was {age_hours:.1f} hours ago")
    return None


def main() -> int:
    config = load_json(CONFIG_PATH, {})
    index = load_json(INDEX_PATH, {"dates": []})
    if not index["dates"]:
        print("no results available")
        return 0

    latest_date = sorted(index["dates"])[-1]
    latest_results = load_json(RESULTS_DIR / f"{latest_date}.json", {"results": []}).get("results", [])
    history = load_json(ALERTS_PATH, {"alerts": []})
    alerts_by_id = {item["id"]: item for item in history.get("alerts", [])}
    now = datetime.utcnow()
    baseline = compute_baseline(index, latest_date)
    active_ids: set[str] = set()

    for result in latest_results:
        tuple_key = (result["hardware"], result["model"])
        candidate_alerts = check_absolute_thresholds(result, config) + check_regressions(
            result,
            baseline.get(tuple_key, {}),
            config,
        )
        for alert in candidate_alerts:
            item_id = alert_id(result, alert["metric"], alert["level"], alert["kind"])
            active_ids.add(item_id)
            existing = alerts_by_id.get(item_id)
            if existing and within_cooldown(existing, now):
                existing["last_seen"] = result["timestamp"]
                continue

            message = format_alert_message(result, alert)
            send_wechat(message, os.getenv("WECHAT_WEBHOOK"))
            send_email(message)
            record = {
                "id": item_id,
                "hardware": result["hardware"],
                "model": result["model"],
                "metric": alert["metric"],
                "level": alert["level"],
                "kind": alert["kind"],
                "first_triggered": existing.get("first_triggered", result["timestamp"]) if existing else result["timestamp"],
                "last_triggered": result["timestamp"],
                "last_seen": result["timestamp"],
                "suppressed_until": (now + timedelta(hours=24)).isoformat(),
                "resolved": False,
            }
            if "baseline" in alert:
                record["baseline"] = alert["baseline"]
                record["delta"] = alert["delta"]
            alerts_by_id[item_id] = record

    latest_timestamp = max((result["timestamp"] for result in latest_results), default=now.isoformat())
    resolve_cleared_alerts(alerts_by_id, active_ids, latest_timestamp)
    payload = {"alerts": sorted(alerts_by_id.values(), key=lambda item: item["last_triggered"], reverse=True)}
    save_json(ALERTS_PATH, payload)
    print(f"tracked {len(payload['alerts'])} alerts")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
