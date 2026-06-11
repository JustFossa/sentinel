"""End-to-end checks on the reasoning engine (mock mode, no network).

Run: PYTHONPATH=src python -m pytest -q     (or: python tests/test_pipeline.py)
"""

from __future__ import annotations

import json
from pathlib import Path

from sentinel.config import Config
from sentinel.main import _load_alert
from sentinel.orchestrator import SentinelOrchestrator

ROOT = Path(__file__).resolve().parents[1]


def _run(name: str):
    scenario = json.loads((ROOT / "scenarios" / f"{name}.json").read_text())
    cfg = Config(mode="mock")
    return SentinelOrchestrator(cfg).run(_load_alert(scenario), scenario)


def test_checkout_is_a_bad_deploy():
    res = _run("checkout_500")
    rc = res.root_cause
    assert rc.offending_change is not None
    assert "a3f9c21" in rc.offending_change
    assert rc.confidence >= 0.8
    # deploy hypothesis confirmed; dependency + infra + config eliminated
    elim = " ".join(rc.eliminated)
    assert "H2" in elim and "H3" in elim and "H4" in elim
    assert "rollback" in rc.recommended_action.lower() or "roll back" in rc.recommended_action.lower()
    assert res.postmortem_markdown.strip().startswith("# Postmortem")


def test_api_latency_is_infra_not_deploy():
    res = _run("api_latency_infra")
    rc = res.root_cause
    # no code change should be implicated here
    assert rc.offending_change is None
    # the winning category should be infra-driven remediation
    assert "scale out" in rc.recommended_action.lower() or "connection-pool" in rc.recommended_action.lower()


if __name__ == "__main__":
    test_checkout_is_a_bad_deploy()
    test_api_latency_is_infra_not_deploy()
    print("ok: both scenarios reason to the correct, distinct root causes")
