"""Sentinel CLI.

    python -m sentinel --scenario checkout_500           # offline demo (default)
    python -m sentinel --scenario api_latency_infra       # different root cause
    python -m sentinel --mode live --scenario checkout_500  # Foundry + MCP
    python -m sentinel --list                              # list scenarios
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from .config import Config
from .models import IncidentAlert
from .orchestrator import SentinelOrchestrator

# repo-root/scenarios (works whether installed or run from source)
SCENARIO_DIRS = [
    Path(__file__).resolve().parents[2] / "scenarios",
    Path.cwd() / "scenarios",
]


def _scenario_dir() -> Path:
    for d in SCENARIO_DIRS:
        if d.exists():
            return d
    return SCENARIO_DIRS[0]


def _resolve_scenario(name: str) -> Path:
    p = Path(name)
    if p.exists():
        return p
    cand = _scenario_dir() / (name if name.endswith(".json") else f"{name}.json")
    if cand.exists():
        return cand
    sys.exit(f"Scenario not found: {name}. Try --list.")


def _load_alert(scenario: dict) -> IncidentAlert:
    a = scenario["alert"]
    return IncidentAlert(
        id=a["id"], service=a["service"], title=a["title"], severity=a["severity"],
        fired_at=a["fired_at"], summary=a["summary"], signals=a.get("signals", {}),
    )


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="sentinel", description="Autonomous incident RCA agent")
    ap.add_argument("--mode", choices=["mock", "live"], default=None,
                    help="mock = offline demo (default); live = Foundry + MCP")
    ap.add_argument("--scenario", default="checkout_500", help="scenario name or path")
    ap.add_argument("--out", default=None, help="write the postmortem markdown here")
    ap.add_argument("--list", action="store_true", help="list available scenarios")
    args = ap.parse_args(argv)

    if args.list:
        for f in sorted(_scenario_dir().glob("*.json")):
            print(f"  {f.stem}")
        return 0

    cfg = Config.load(mode_override=args.mode)
    scenario = json.loads(_resolve_scenario(args.scenario).read_text(encoding="utf-8"))
    alert = _load_alert(scenario)

    orchestrator = SentinelOrchestrator(cfg)
    resolution = orchestrator.run(alert, scenario)

    out = Path(args.out) if args.out else (Path.cwd() / "out" / f"{alert.id}.postmortem.md")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(resolution.postmortem_markdown, encoding="utf-8")
    print(f"\nPostmortem written to: {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
