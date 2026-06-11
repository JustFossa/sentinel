# Contributing to Sentinel

Thanks for your interest! Sentinel is a multi-agent incident root-cause reasoning
system. The easiest ways to contribute are new **scenarios**, new **investigators**,
or new **MCP tool integrations**.

## Dev setup

```bash
git clone https://github.com/JustFossa/sentinel && cd sentinel
PYTHONPATH=src python -m sentinel --scenario checkout_500   # offline, no deps
PYTHONPATH=src python tests/test_pipeline.py                # run the tests
```

For live mode: `pip install "sentinel-rca[live]"` and fill in `.env` (see `.env.example`).

## Adding a scenario

1. Drop a JSON file in `scenarios/` matching the shape of `checkout_500.json`
   (`alert`, `telemetry`, `metrics`, `config_changes`, `deploys`, `runbooks`).
2. Run `python -m sentinel --scenario <name>` and confirm the verdict is correct.
3. Add an assertion to `tests/test_pipeline.py`.

## Adding an investigator

1. Add a class in `src/sentinel/agents/investigators.py` that returns an
   `InvestigationReport`. Tag every `Evidence` with the hypotheses it
   `supports` or `refutes` — the elimination logic depends on it.
2. Wire it into `orchestrator.py` (and the MAF composition in `maf_workflow.py`).

## Ground rules

- **Reasoning stays grounded.** Conclusions must trace to tagged evidence.
- **No secrets committed.** `.env` is gitignored; keep it that way.
- CI must pass: `tests/test_pipeline.py` plus the two scenario smoke tests.

## Conduct

Be respectful and constructive. Assume good faith.
