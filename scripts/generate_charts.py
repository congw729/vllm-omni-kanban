from __future__ import annotations

import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.common import flatten_metrics, load_json, save_json

DATA_DIR = ROOT / "data"
RESULTS_DIR = DATA_DIR / "results"
INDEX_PATH = DATA_DIR / "index.json"
CONFIG_PATH = DATA_DIR / "config.json"
ALERTS_PATH = DATA_DIR / "alerts.json"
CHARTS_DIR = ROOT / "docs" / "assets" / "charts"

def save_chart(name: str, option: dict[str, Any]) -> None:
    save_json(CHARTS_DIR / f"{name}.json", option)


def average_metric(results: list[dict[str, Any]], metric: str) -> float | None:
    values = [value for result in results if isinstance((value := flatten_metrics(result["metrics"]).get(metric)), (int, float))]
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def build_line_chart(dates: list[str], values: list[float | None], title: str, y_min: float | None = None, y_max: float | None = None) -> dict[str, Any]:
    return {
        "title": {"text": title},
        "tooltip": {"trigger": "axis"},
        "xAxis": {"type": "category", "data": dates},
        "yAxis": {"type": "value", "min": y_min, "max": y_max},
        "series": [{"type": "line", "data": values, "smooth": True}],
    }


def build_heatmap(config: dict[str, Any], latest_results: list[dict[str, Any]]) -> dict[str, Any]:
    hardware_keys = list(config["hardware"].keys())
    model_keys = list(config["models"].keys())
    values = []
    lookup = {(item["model"], item["hardware"]): flatten_metrics(item["metrics"]).get("pass_rate") for item in latest_results}
    for model_index, model in enumerate(model_keys):
        for hw_index, hardware in enumerate(hardware_keys):
            values.append([hw_index, model_index, lookup.get((model, hardware))])

    return {
        "title": {"text": "Latest Pass Rate Heatmap"},
        "tooltip": {},
        "xAxis": {"type": "category", "data": hardware_keys},
        "yAxis": {"type": "category", "data": model_keys},
        "visualMap": {"min": 0, "max": 1, "calculable": True, "orient": "horizontal"},
        "series": [{"type": "heatmap", "data": values}],
    }


def build_summary(index: dict[str, Any], latest_results: list[dict[str, Any]], alerts: dict[str, Any]) -> dict[str, Any]:
    if not latest_results:
        return {"latest_date": None, "overall_pass_rate": None, "overall_latency_p99_ms": None, "latest_commit": None, "recent_alerts": 0}
    return {
        "latest_date": sorted(index.get("dates", []))[-1],
        "overall_pass_rate": average_metric(latest_results, "pass_rate"),
        "overall_latency_p99_ms": average_metric(latest_results, "latency_p99_ms"),
        "latest_commit": max(latest_results, key=lambda item: item["timestamp"])["commit"],
        "recent_alerts": len([item for item in alerts.get("alerts", []) if not item.get("resolved")]),
    }


def main() -> int:
    config = load_json(CONFIG_PATH, {})
    index = load_json(INDEX_PATH, {"dates": []})
    alerts = load_json(ALERTS_PATH, {"alerts": []})
    dates = sorted(index.get("dates", []))
    day_results = {date: load_json(RESULTS_DIR / f"{date}.json", {"results": []}).get("results", []) for date in dates}

    pass_rate_values = [average_metric(day_results[date], "pass_rate") for date in dates]
    latency_values = [average_metric(day_results[date], "latency_p99_ms") for date in dates]

    save_chart("pass_rate_trend_7d", build_line_chart(dates[-7:], pass_rate_values[-7:], "Pass Rate (7d)", 0, 1))
    save_chart("pass_rate_trend_30d", build_line_chart(dates[-30:], pass_rate_values[-30:], "Pass Rate (30d)", 0, 1))
    save_chart("latency_p99_trend_7d", build_line_chart(dates[-7:], latency_values[-7:], "Latency P99 (7d)"))
    latest_results = day_results[dates[-1]] if dates else []
    save_chart("pass_rate_heatmap", build_heatmap(config, latest_results))
    save_chart("summary", build_summary(index, latest_results, alerts))
    print(f"generated {len(list(CHARTS_DIR.glob('*.json')))} chart files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
