from __future__ import annotations

import argparse
import os
import sys

import requests
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
from scripts.common import save_json


def validate_batch(payload: object) -> list[dict]:
    if isinstance(payload, list):
        results = payload
    elif isinstance(payload, dict) and isinstance(payload.get("results"), list):
        results = payload["results"]
    else:
        raise ValueError("expected a JSON list or an object with a 'results' list")

    if not results:
        raise ValueError("batch payload is empty")
    if not all(isinstance(item, dict) for item in results):
        raise ValueError("batch payload must contain result objects")
    return results


def fetch_batch(url: str, token: str | None = None, timeout: int = 30) -> list[dict]:
    response = requests.get(url, headers={"Authorization": f"Bearer {token}"} if token else {}, timeout=timeout)
    response.raise_for_status()
    return validate_batch(response.json())


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Fetch the latest daily results batch.")
    parser.add_argument("--output", required=True, help="Output JSON file path")
    parser.add_argument("--url", help="Override results source URL")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    url = args.url or os.getenv("RESULTS_SOURCE_URL")
    token = os.getenv("RESULTS_SOURCE_TOKEN")
    if not url:
        raise SystemExit("missing RESULTS_SOURCE_URL or --url")

    batch = fetch_batch(url, token=token)
    save_json(Path(args.output), {"results": batch})
    print(f"wrote {len(batch)} results to {args.output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
