"""Unit tests for build_hardware_status()."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_charts import build_hardware_status


def test_empty_data():
    """Test empty data returns empty list."""
    config = {"hardware": {}}
    results = []
    result = build_hardware_status(config, results)
    assert result == {"hardware": []}


def test_missing_metrics():
    """Test missing metrics handled correctly."""
    config = {"hardware": {"h1": {"display_name": "H1"}}}
    results = [
        {"model": "q1", "hardware": "h1", "metrics": {}},
    ]
    result = build_hardware_status(config, results)
    # When metrics are missing, pass_rate and latency should be None
    assert len(result["hardware"]) == 1
    assert result["hardware"][0]["display_name"] == "H1"
    assert result["hardware"][0]["pass_rate"] is None
    assert result["hardware"][0]["latency_p99_ms"] is None


def test_status_thresholds():
    """Test status thresholds: healthy >= 90%, warning >= 80%, critical < 80%."""
    config = {"hardware": {"h1": {"display_name": "H1"}, "h2": {"display_name": "H2"}, "h3": {"display_name": "H3"}}}
    results = [
        {"model": "q1", "hardware": "h1", "metrics": {"pass_rate": 0.95}},
        {"model": "q1", "hardware": "h2", "metrics": {"pass_rate": 0.85}},
        {"model": "q1", "hardware": "h3", "metrics": {"pass_rate": 0.75}},
    ]
    result = build_hardware_status(config, results)
    
    # h1: 95% -> healthy
    assert result["hardware"][0]["status"] == "healthy"
    # h2: 85% -> warning
    assert result["hardware"][1]["status"] == "warning"
    # h3: 75% -> critical
    assert result["hardware"][2]["status"] == "critical"


def test_average_across_models():
    """Test pass_rate averaging across multiple models."""
    config = {"hardware": {"h1": {"display_name": "H1"}}}
    results = [
        {"model": "q1", "hardware": "h1", "metrics": {"pass_rate": 0.9}},
        {"model": "q2", "hardware": "h1", "metrics": {"pass_rate": 0.8}},
    ]
    result = build_hardware_status(config, results)
    # Average: (0.9 + 0.8) / 2 = 0.85 -> warning
    assert result["hardware"][0]["pass_rate"] == 0.85
    assert result["hardware"][0]["status"] == "warning"


def test_latency_calculation():
    """Test latency_p99_ms averaging."""
    config = {"hardware": {"h1": {"display_name": "H1"}}}
    results = [
        {"model": "q1", "hardware": "h1", "metrics": {"pass_rate": 0.9, "latency_p99_ms": 100.0}},
        {"model": "q2", "hardware": "h1", "metrics": {"pass_rate": 0.9, "latency_p99_ms": 200.0}},
    ]
    result = build_hardware_status(config, results)
    # Average: (100 + 200) / 2 = 150
    assert result["hardware"][0]["latency_p99_ms"] == 150.0


if __name__ == "__main__":
    import pytest
    pytest.main([__file__, "-v"])
