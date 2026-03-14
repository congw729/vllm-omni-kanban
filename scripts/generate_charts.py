from __future__ import annotations

import sys
from collections import Counter
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
MODEL_METRICS = [
    ("latency_p99_ms", "Latency P99 (ms)", None, None),
    ("throughput_tokens_per_sec", "Throughput", None, None),
    ("ttft_ms", "TTFT (ms)", None, None),
    ("benchmark_score", "Benchmark Score", 0, 1),
]
RANGE_WINDOWS = {"1d": 1, "7d": 7, "30d": 30}

def save_chart(name: str, option: dict[str, Any]) -> None:
    save_json(CHARTS_DIR / f"{name}.json", option)


def average_metric(results: list[dict[str, Any]], metric: str) -> float | None:
    values = [value for result in results if isinstance((value := flatten_metrics(result["metrics"]).get(metric)), (int, float))]
    if not values:
        return None
    return round(sum(values) / len(values), 4)


def build_line_chart(
    dates: list[str],
    values: list[float | None],
    y_min: float | None = None,
    y_max: float | None = None,
) -> dict[str, Any]:
    return {
        "tooltip": {"trigger": "axis"},
        "grid": {"left": 56, "right": 24, "top": 36, "bottom": 42},
        "xAxis": {"type": "category", "data": dates, "axisLabel": {"color": "#5b6775"}},
        "yAxis": {"type": "value", "min": y_min, "max": y_max},
        "series": [{"type": "line", "data": values, "smooth": True, "symbolSize": 7, "lineStyle": {"width": 3}}],
    }


def chart_slug(value: str) -> str:
    return value.lower().replace(".", "").replace(" ", "_").replace("-", "_")


def build_multi_series_chart(
    dates: list[str],
    hardware_items: list[tuple[str, str]],
    day_results: dict[str, list[dict[str, Any]]],
    model: str,
    metric: str,
    y_min: float | None = None,
    y_max: float | None = None,
) -> dict[str, Any]:
    series = []
    for hardware, hardware_label in hardware_items:
        values = []
        for date in dates:
            match = next(
                (item for item in day_results.get(date, []) if item["model"] == model and item["hardware"] == hardware),
                None,
            )
            flat = flatten_metrics(match["metrics"]) if match else {}
            values.append(flat.get(metric))
        if any(value is not None for value in values):
            series.append({"name": hardware_label, "type": "line", "data": values, "smooth": True})

    return {
        "tooltip": {"trigger": "axis"},
        "legend": {"type": "scroll", "top": 0, "left": 0, "right": 0, "textStyle": {"fontSize": 12}},
        "grid": {"left": 56, "right": 24, "top": 54, "bottom": 42},
        "xAxis": {"type": "category", "data": dates, "axisLabel": {"color": "#5b6775"}},
        "yAxis": {"type": "value", "min": y_min, "max": y_max, "axisLabel": {"color": "#5b6775"}},
        "series": series,
    }


def build_heatmap(config: dict[str, Any], latest_results: list[dict[str, Any]]) -> dict[str, Any]:
    hardware_keys = list(config["hardware"].keys())
    hardware_labels = [config["hardware"][hardware]["display_name"] for hardware in hardware_keys]
    model_keys = list(config["models"].keys())
    model_labels = [config["models"][model]["display_name"] for model in model_keys]
    values = []
    lookup = {(item["model"], item["hardware"]): flatten_metrics(item["metrics"]).get("pass_rate") for item in latest_results}
    for model_index, model in enumerate(model_keys):
        for hw_index, hardware in enumerate(hardware_keys):
            values.append([hw_index, model_index, lookup.get((model, hardware))])

    return {
        "tooltip": {},
        "grid": {"left": 128, "right": 96, "top": 18, "bottom": 58},
        "xAxis": {"type": "category", "data": hardware_labels, "axisLabel": {"interval": 0, "rotate": 18, "fontSize": 11}},
        "yAxis": {"type": "category", "data": model_labels, "axisLabel": {"fontSize": 11}},
        "visualMap": {
            "min": 0,
            "max": 1,
            "calculable": True,
            "orient": "vertical",
            "right": 18,
            "top": "middle",
            "inRange": {"color": ["#c84d57", "#f2d27a", "#60b27c"]},
        },
        "series": [{"type": "heatmap", "data": values}],
    }


def build_summary(index: dict[str, Any], latest_results: list[dict[str, Any]], alerts: dict[str, Any]) -> dict[str, Any]:
    active_alerts = [item for item in alerts.get("alerts", []) if not item.get("resolved")]
    level_counts = Counter(item.get("level", "warning") for item in active_alerts)
    if not latest_results:
        return {
            "latest_date": None,
            "overall_pass_rate": None,
            "overall_latency_p99_ms": None,
            "latest_commit": None,
            "recent_alerts": 0,
            "warning_alerts": 0,
            "critical_alerts": 0,
        }
    return {
        "latest_date": sorted(index.get("dates", []))[-1],
        "overall_pass_rate": average_metric(latest_results, "pass_rate"),
        "overall_latency_p99_ms": average_metric(latest_results, "latency_p99_ms"),
        "latest_commit": max(latest_results, key=lambda item: item["timestamp"])["commit"],
        "recent_alerts": len(active_alerts),
        "warning_alerts": level_counts.get("warning", 0),
        "critical_alerts": level_counts.get("critical", 0),
    }


def main() -> int:
    config = load_json(CONFIG_PATH, {})
    index = load_json(INDEX_PATH, {"dates": []})
    alerts = load_json(ALERTS_PATH, {"alerts": []})
    dates = sorted(index.get("dates", []))
    day_results = {date: load_json(RESULTS_DIR / f"{date}.json", {"results": []}).get("results", []) for date in dates}

    pass_rate_values = [average_metric(day_results[date], "pass_rate") for date in dates]
    latency_values = [average_metric(day_results[date], "latency_p99_ms") for date in dates]
    hardware_items = [(key, value["display_name"]) for key, value in config.get("hardware", {}).items()]

    for range_key, window in RANGE_WINDOWS.items():
        save_chart(
            f"pass_rate_trend_{range_key}",
            build_line_chart(dates[-window:], pass_rate_values[-window:], 0, 1),
        )
        save_chart(
            f"latency_p99_trend_{range_key}",
            build_line_chart(dates[-window:], latency_values[-window:]),
        )
    latest_results = day_results[dates[-1]] if dates else []
    save_chart("pass_rate_heatmap", build_heatmap(config, latest_results))
    save_chart("summary", build_summary(index, latest_results, alerts))
    for model, model_config in config.get("models", {}).items():
        available_metrics = set(model_config["metrics"]["required"]) | set(model_config["metrics"]["optional"])
        for metric, label, y_min, y_max in MODEL_METRICS:
            if metric not in available_metrics:
                continue
            for range_key, window in RANGE_WINDOWS.items():
                save_chart(
                    f"{chart_slug(model)}_{metric}_{range_key}",
                    build_multi_series_chart(
                        dates[-window:],
                        hardware_items,
                        day_results,
                        model,
                        metric,
                        y_min=y_min,
                        y_max=y_max,
                    ),
                )
    print(f"generated {len(list(CHARTS_DIR.glob('*.json')))} chart files")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
