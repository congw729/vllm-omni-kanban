from __future__ import annotations

import subprocess
import sys
from pathlib import Path


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
