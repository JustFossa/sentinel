# 🛡️ Sentinel — Autonomous Incident Root-Cause Reasoning Agent

> When production breaks at 3am, Sentinel does what a senior on-call engineer
> does: forms competing hypotheses, gathers evidence from your telemetry and your
> git history, **eliminates** causes one by one, **double-checks its own logic**,
> and hands you the root cause, a fix, and a postmortem — in seconds.

Built for the **Reasoning Agents** track on **Microsoft Foundry**, using the
**Microsoft Agent Framework**, **Azure MCP**, and the **GitHub MCP**.

[![CI](https://github.com/JustFossa/sentinel/actions/workflows/ci.yml/badge.svg)](https://github.com/JustFossa/sentinel/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![License](https://img.shields.io/badge/license-MIT-green)

[Architecture](ARCHITECTURE.md) · [Demo script](DEMO_SCRIPT.md) · [Project description](PROJECT_DESCRIPTION.md)

---

## The problem

Root-cause analysis is the slowest, most expensive part of every incident. The
data needed to solve it is *already there* — logs, metrics, recent deploys — but
it's scattered across App Insights, Azure Monitor, and GitHub, and a human has to
manually correlate it under pressure. MTTR is dominated by *diagnosis*, not the
fix.

## The solution

Sentinel is a **multi-agent reasoning system**, not a log summarizer. It runs a
real diagnostic loop:

```
PLAN ─▶ INVESTIGATE (fan-out) ─▶ SYNTHESIZE ─▶ CRITIQUE
                                      ▲             │
                                      └── targeted ─┘   (self-correction)
                                          follow-up
```

| Agent | Job |
|-------|-----|
| 🧭 **Planner** | Decomposes the alert into 3–5 competing, testable hypotheses (deploy / dependency / infra / config). |
| 🔎 **Log Investigator** | Queries App Insights via **Azure MCP** — exceptions, 5xx series, dependency health. Tags each finding *supports/refutes*. |
| 🧬 **Code Investigator** | Correlates recent deploys/diffs via the **GitHub MCP** to find the change that touched the failing path. |
| 🖥️ **Infra Investigator** | Reads Azure Monitor metrics + activity log via **Azure MCP** to rule resource pressure and config changes in or out. |
| 🧮 **Synthesizer** | Eliminates refuted hypotheses; elevates the survivor to a root cause with a remediation. |
| 🧪 **Critic** | Adversarially verifies causality (did errors begin *after* the deploy?). If not proven, it sends the team back for a targeted follow-up. |
| 📝 **Postmortem Writer** | Produces a blameless postmortem with timeline, evidence, and action items. |

The reasoning is **grounded**: every conclusion traces back to a tagged piece of
evidence, and the Critic won't approve a verdict below 0.80 confidence.

---

## Quickstart — 30-second offline demo (no keys, no Azure, no network)

```bash
git clone <your-repo-url> && cd sentinel
pip install -e .            # registers the package — pulls ZERO third-party deps
python -m sentinel --scenario checkout_500
```

`pip install -e .` only puts the `sentinel` package on Python's import path; mock
mode itself runs on the **standard library only**, so no third-party packages are
installed (`dependencies = []`). Prefer not to install anything at all? Point
Python at the source tree instead:

```bash
# bash / macOS / Linux / Git Bash
PYTHONPATH=src python -m sentinel --scenario checkout_500
# Windows PowerShell
$env:PYTHONPATH = "src"; python -m sentinel --scenario checkout_500
```

You'll watch the agents reason live in your terminal and get a postmortem in
`out/INC-4471.postmortem.md`. See **[USAGE.md](USAGE.md)** for the full testing guide.

Try the second scenario to see the *same engine reach a different conclusion*:

```bash
python -m sentinel --scenario api_latency_infra   # → infra (pool exhaustion), not a deploy
python -m sentinel --list                          # list scenarios
```

> Optional: `pip install rich` for colorized trace output (auto-detected).

---

## Live mode — real Microsoft Foundry + MCP

```bash
pip install "sentinel-rca[live]"      # or: pip install -r requirements.txt
cp .env.example .env                  # fill in Foundry + Azure + GitHub values
python -m sentinel --mode live --scenario checkout_500
```

Live mode:
- runs the agents as a **Microsoft Agent Framework** workflow (`src/sentinel/maf_workflow.py`)
  on a **Foundry** reasoning deployment (GPT-5.2 / MAI-Thinking-1);
- connects the **Azure MCP** server (`npx -y @azure/mcp@latest server start`) for
  live App Insights / Azure Monitor queries;
- connects the hosted **GitHub MCP** server for deploy/diff correlation;
- ships every model call, tool hop, and handoff to the **Foundry Control Plane**
  via OpenTelemetry (`OTEL_EXPORTER_OTLP_ENDPOINT`).

### Reproduce the incident yourself (optional)

```bash
pip install flask
python sample_app/app.py                            # healthy: checkout returns 200
CHECKOUT_VERSION=buggy python sample_app/app.py      # reproduces commit a3f9c21 → 500s
```

---

## Repo layout

```
sentinel/
├── src/sentinel/
│   ├── orchestrator.py     # the reasoning engine (PLAN→INVESTIGATE→SYNTH→CRITIQUE loop)
│   ├── maf_workflow.py     # LIVE: Microsoft Agent Framework composition on Foundry
│   ├── agents/             # planner, investigators, synthesizer, critic, postmortem
│   ├── tools.py            # Azure MCP + GitHub MCP tool clients (mock + live)
│   ├── mcp_client.py       # MCP transport (stdio + streamable-http)
│   ├── llm.py              # Foundry / Azure OpenAI reasoning client
│   ├── tracing.py          # console trace + OpenTelemetry spans
│   ├── models.py           # Hypothesis / Evidence / RootCause artifacts
│   └── main.py             # CLI
├── scenarios/              # canned incidents (checkout_500, api_latency_infra)
├── sample_app/             # tiny Flask checkout service that breaks on cue
├── architecture.svg        # architecture diagram
└── ARCHITECTURE.md  DEMO_SCRIPT.md  PROJECT_DESCRIPTION.md
```

## Why it wins the Reasoning track

It showcases the thing the track is judged on: **multi-step reasoning that solves
a hard problem.** Hypotheses are generated, evidence is gathered and tagged,
causes are eliminated deductively, and the agent *critiques and corrects itself*
before committing. The proof it's reasoning and not scripted: it reaches two
different, correct root causes on two different incidents with the same code.

## License
MIT
