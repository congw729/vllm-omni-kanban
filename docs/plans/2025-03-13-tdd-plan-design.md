# vLLM-Omni Kanban TDD Plan

**Date:** 2025-03-13
**Status:** Approved
**Author:** Brainstorming session

## Overview

Test-Driven Development plan for vLLM-Omni Kanban using pytest. Focus on core Python scripts with fixtures-based testing.

## 1. Test Structure

```
vllm-omni-kanban/
├── tests/
│   ├── conftest.py              # Shared fixtures (sample CI data)
│   ├── test_process_results.py  # Unit tests for data processing
│   ├── test_generate_charts.py  # Unit tests for chart generation
│   └── test_check_alerts.py     # Unit tests for alerting logic
├── pytest.ini                   # pytest configuration
└── requirements.txt             # includes pytest, pytest-cov
```

## 2. Test Fixtures (`conftest.py`)

Sample CI result fixtures covering:

- `valid_minimal`: bare minimum required fields
- `valid_full`: all fields populated
- `edge_cases`: missing optional fields, extreme values
- `invalid`: malformed data for validation tests
- `multi_hardware`: 5 hardware types × 5 models matrix
- `time_series`: 7 days of data for trend/regression tests

Key fixtures:

| Fixture | Purpose |
|---------|---------|
| `sample_ci_result` | Single valid result |
| `sample_results_json` | 90-day rolling data structure |
| `sample_config` | Hardware/models/thresholds config |
| `regression_baseline` | 7-day averages for comparison |

## 3. Test Cases by Script

### `test_process_results.py`

| Test | Description |
|------|-------------|
| `test_append_result` | New result appends to results.json |
| `test_prune_old_data` | Results older than 90 days are removed |
| `test_validate_schema` | Invalid results raise ValidationError |
| `test_generate_daily_report` | Markdown report generated correctly |
| `test_handle_missing_fields` | Missing optional fields don't crash |

### `test_generate_charts.py`

| Test | Description |
|------|-------------|
| `test_line_chart_data` | Time series data formatted for ECharts |
| `test_heatmap_matrix` | Model × Hardware matrix generated |
| `test_empty_data_handling` | Graceful handling of missing data |
| `test_date_range_filtering` | 7-day vs 30-day filtering works |

### `test_check_alerts.py`

| Test | Description |
|------|-------------|
| `test_absolute_threshold_critical` | Pass rate < 80% triggers critical |
| `test_absolute_threshold_warning` | Pass rate < 90% triggers warning |
| `test_regression_detection` | 20% latency spike detected vs baseline |
| `test_no_false_positives` | Normal variation doesn't alert |
| `test_alert_format` | Notification message formatted correctly |

## 4. TDD Workflow Per Script

Cycle per feature:

```
1. Write failing test → 2. Write minimal code → 3. Test passes → 4. Refactor
         ↑                                                        |
         +--------------------------------------------------------+
```

Implementation order:

| Phase | Script | Why First |
|-------|--------|-----------|
| 1 | `process_results.py` | Core data layer, everything depends on it |
| 2 | `check_alerts.py` | Business logic, independent of visualization |
| 3 | `generate_charts.py` | Depends on processed data format |

Per-phase checklist:

- [ ] Write tests for one function/feature
- [ ] Run `pytest -x` (fail)
- [ ] Implement minimal code to pass
- [ ] Run `pytest` (pass)
- [ ] Refactor if needed
- [ ] Repeat for next feature

## 5. Test Commands & Coverage

**pytest.ini:**

```ini
[pytest]
testpaths = tests
python_files = test_*.py
addopts = -v --tb=short
```

**Commands:**

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=scripts --cov-report=term-missing

# Run specific test file
pytest tests/test_process_results.py

# Run single test
pytest tests/test_process_results.py::test_append_result
```

**Coverage target:** 80% for initial implementation
