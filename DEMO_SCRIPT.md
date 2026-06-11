# Sentinel — 2-Minute Demo Script (shot-by-shot)

Goal: prove Sentinel *reasons* — forms hypotheses, gathers evidence, eliminates
causes, corrects itself — and lands a verified root cause + postmortem.

Record at 1080p. Terminal font ≥ 18pt. `pip install rich` first for color.
Total budget: **120 seconds.**

---

### 0:00–0:15 — The hook (problem)
**On screen:** title slide → cut to terminal.
**Say:** "It's 3am. Checkout is throwing 500s and you're losing $7k a minute.
Finding *why* means digging through App Insights, Azure Monitor, and your git
history by hand. Sentinel does that diagnosis for you — autonomously."

### 0:15–0:25 — Kick it off
**Do:** run
```bash
python -m sentinel --scenario checkout_500
```
**Say:** "One command. Watch it think — these are real agents on Microsoft
Foundry, built with the Microsoft Agent Framework."

### 0:25–0:40 — PLAN
**On screen:** the `1 · PLAN` stage printing H1–H4.
**Say:** "First it doesn't guess. The Planner breaks the incident into four
*competing* hypotheses — bad deploy, failing dependency, infra, config — and
assigns each to a specialist."

### 0:40–1:00 — INVESTIGATE (the MCP moment)
**On screen:** the three investigators printing `⛁ azure_mcp …` / `⛁ github_mcp …`
tool calls and ✓/✗ findings.
**Say:** "Three agents fan out in parallel. Through **Azure MCP** they query App
Insights and Azure Monitor; through the **GitHub MCP** they pull recent deploys.
Notice — they're not summarizing. Every finding is tagged: this *supports* the
deploy hypothesis, this *refutes* the dependency one. Dependencies healthy. Infra
healthy. No config change."

### 1:00–1:20 — SYNTHESIZE + the self-correction beat (the differentiator)
**On screen:** Synthesizer eliminating H2/H3/H4; Critic printing "Temporal
ordering not yet verified — requesting follow-up", then the Log Investigator
re-querying, then "Verified: errors began AFTER deploy. Causality holds."
**Say:** "Here's the part that makes it a *reasoning* agent. It eliminates the
refuted causes — but before committing, the Critic catches that it hasn't *proven*
the timeline. So it sends an agent back to confirm the errors started *after* the
deploy. It corrects itself, then raises its confidence."

### 1:20–1:40 — The verdict
**On screen:** the green `✅ SENTINEL VERDICT` panel — commit `a3f9c21`, the
removed `tax_rate` fallback, recommended rollback, ~95% confidence.
**Say:** "Verdict: commit a3f9c21, 'simplify tax calculation', removed a fallback
and broke checkout for items with no tax category. Ninety-five percent confidence.
Recommended action: roll it back."

### 1:40–1:55 — It actually reasons (proof) + postmortem
**Do:** run
```bash
python -m sentinel --scenario api_latency_infra
```
and flash the postmortem file.
**Say:** "Same agent, a different incident — and it reaches a *different* correct
answer: connection-pool exhaustion, not a deploy. That's reasoning, not a script.
And every run ships a blameless postmortem automatically."

### 1:55–2:00 — Close
**On screen:** architecture.svg.
**Say:** "Sentinel — multi-step incident reasoning on Microsoft Foundry. Thanks."

---

## Pre-flight checklist
- [ ] `pip install -e .` (one-time — puts `sentinel` on the import path; zero third-party deps)
- [ ] `pip install rich` (color trace)
- [ ] Terminal cleared, font ≥ 18pt, dark theme
- [ ] Dry-run both scenarios once so timing feels natural
- [ ] Have `out/INC-4471.postmortem.md` open in a second pane to flash
- [ ] (Optional live shot) Azure MCP running: `npx -y @azure/mcp@latest server start`
- [ ] No secrets/keys visible on screen
