# Sentinel — Autonomous Incident Root-Cause Reasoning Agent

**Track:** Reasoning Agents (Microsoft Foundry)
**Built with:** Microsoft Foundry · Microsoft Agent Framework · Azure MCP · GitHub MCP · Azure Monitor / App Insights · GitHub Copilot

## The problem it solves

For every production incident, the clock that matters is **MTTR** — and MTTR is
dominated by *diagnosis*, not the fix. The evidence needed to find a root cause
already exists, but it's fragmented across three places no single tool spans:
application telemetry (App Insights), infrastructure metrics (Azure Monitor), and
source history (GitHub). At 3am, a human has to manually pull threads from all
three and correlate them under pressure. That correlation is slow, error-prone,
and doesn't scale across a fleet of services.

## What Sentinel does

Sentinel is a **multi-agent reasoning system** that performs the diagnosis a
senior on-call engineer would — autonomously. Given an alert, it:

1. **Plans** — decomposes the incident into 3–5 competing, testable hypotheses
   (bad deploy, failing dependency, resource exhaustion, config change).
2. **Investigates** — three specialist agents fan out concurrently and gather
   evidence through MCP tools: the Log Investigator runs KQL against App Insights
   via **Azure MCP**; the Infra Investigator reads Azure Monitor metrics and the
   activity log; the Code Investigator correlates recent deploys and diffs via the
   **GitHub MCP**. Every finding is tagged with the hypotheses it supports or
   refutes.
3. **Synthesizes** — eliminates the refuted hypotheses and elevates the surviving
   one to a root cause, with a concrete remediation.
4. **Critiques itself** — an adversarial Critic verifies causality (e.g. that the
   errors actually began *after* the suspected deploy). If the proof isn't in
   hand, it sends the team back for a targeted follow-up. It refuses to commit to
   a conclusion below 0.80 confidence.
5. **Reports** — writes a blameless postmortem with a timeline, the supporting
   evidence, the eliminated hypotheses, and action items.

## Why it's a *reasoning* agent (and the AI value)

This is the core of the submission. Sentinel does not pattern-match a single
answer or summarize logs — it runs an explicit, multi-step diagnostic loop with
**deductive elimination** and **self-correction**:

- Conclusions are **grounded**: each one traces back to tagged evidence, so the
  reasoning is auditable rather than asserted.
- The agent **changes its mind**: the Critic's follow-up loop is a real feedback
  edge, not decoration.
- The proof it reasons rather than replays: the *same engine* reaches two
  different, correct root causes on two different incidents — a code regression
  on one, infrastructure saturation on the other.

The business value is direct: Sentinel compresses the diagnosis phase of an
incident from tens of minutes of human correlation to seconds, and produces the
postmortem as a byproduct.

## Key features

- Six-role multi-agent workflow (Planner, 3 Investigators, Synthesizer, Critic) plus a Postmortem Writer.
- Concurrent fan-out / fan-in investigation with a synthesize⇄critique self-correction loop.
- Live evidence gathering through **Azure MCP** (App Insights KQL, Azure Monitor metrics, activity log) and the **GitHub MCP** (commits, diffs, deploys).
- Full **OpenTelemetry** instrumentation — every model call, tool hop, and handoff lands in the **Foundry Control Plane** for traces and evals.
- Confidence-gated output and a generated blameless postmortem.
- Runs fully offline in a deterministic **mock mode** (no keys) for instant evaluation, and in **live mode** on real Foundry + Azure resources.
- Includes a sample Flask service that reproduces the demo incident on cue.

## Technologies used

| Layer | Technology |
|-------|-----------|
| Agent orchestration | Microsoft Agent Framework 1.0 (`WorkflowBuilder` fan-out/fan-in + Magentic manager) |
| Reasoning model | Microsoft Foundry deployment — GPT-5.2 / MAI-Thinking-1 |
| Tooling | Azure MCP Server, GitHub MCP Server (Model Context Protocol) |
| Azure services | Azure Monitor, Application Insights, AKS / Container Apps, Cosmos DB |
| Observability | OpenTelemetry → Foundry Control Plane (traces + evals) |
| Build experience | GitHub Copilot / Foundry Toolkit for VS Code |
| Language | Python 3.10+ |

## How to run

Offline demo (no setup): `python -m sentinel --scenario checkout_500`
Live: fill `.env`, then `python -m sentinel --mode live --scenario checkout_500`
See `README.md` for full instructions and `ARCHITECTURE.md` for the diagram.

## Repository

Code repository: **<add your public GitHub URL here>**
Demo video: **<add your YouTube/Vimeo URL here>**
