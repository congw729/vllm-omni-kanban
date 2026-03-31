"""MkDocs hooks: regenerate chart JSON before the first build of each CLI run.

Uses on_startup (not on_pre_build) so writes under docs/assets/charts/ do not
re-trigger livereload in an endless loop; generate_charts updates generated_at every run.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path


def on_startup(command: str, dirty: bool, **kwargs) -> None:
    repo_root = Path(__file__).resolve().parent.parent
    script = repo_root / "scripts" / "generate_charts.py"
    proc = subprocess.run(
        [sys.executable, str(script)],
        cwd=str(repo_root),
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"generate_charts.py exited with status {proc.returncode}")
