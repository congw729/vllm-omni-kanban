from __future__ import annotations

from types import SimpleNamespace

from scripts.fetch_latest_results import fetch_batch


def test_fetch_latest_results_success(sample_daily_batch: dict, monkeypatch) -> None:
    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return sample_daily_batch

    monkeypatch.setattr(
        "scripts.fetch_latest_results.requests.get",
        lambda *args, **kwargs: FakeResponse(),
    )
    batch = fetch_batch("https://example.test/results.json")
    assert len(batch) == 30


def test_fetch_latest_results_auth_header(sample_daily_batch: dict, monkeypatch) -> None:
    captured = {}

    class FakeResponse:
        def raise_for_status(self) -> None:
            return None

        def json(self) -> dict:
            return sample_daily_batch

    def fake_get(url, headers=None, timeout=30):
        captured["headers"] = headers
        return FakeResponse()

    monkeypatch.setattr("scripts.fetch_latest_results.requests.get", fake_get)
    batch = fetch_batch("https://example.test/results.json", token="secret")
    assert len(batch) == 30
    assert captured["headers"]["Authorization"] == "Bearer secret"
