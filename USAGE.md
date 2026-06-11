# Usage & Testing Guide

How to run, test, and demo **Sentinel** locally. Mock mode needs **no keys, no
Azure, no network** — it runs on the Python standard library.

---

## 1. Why `python -m sentinel` failed

The package lives under **`src/sentinel/`** (a "src layout"). When you run
`python -m sentinel` from the repo root, Python looks for a `sentinel` package on
its import path — and `src/` isn't on it by default. That's the
`No module named sentinel` error.

Pick **one** of the two fixes below. Setup A is recommended.

---

## 2. One-time setup

### Setup A — editable install (recommended)

Registers the `sentinel` package on your import path. It pulls **zero**
third-party dependencies (`dependencies = []` in `pyproject.toml`), so mock mode
stays stdlib-only.

```powershell
# from the repo root: C:\Users\Lenovo\Desktop\hackathon\sentinel
python -m pip install -e .
```

After this, `python -m sentinel ...` works from anywhere.

### Setup B — no install (point Python at the source tree)

If you'd rather not install anything, set `PYTHONPATH` to `src` for the command:

```powershell
# Windows PowerShell
$env:PYTHONPATH = "src"; python -m sentinel --scenario checkout_500
```

```bash
# Git Bash / macOS / Linux
PYTHONPATH=src python -m sentinel --scenario checkout_500
```

> In PowerShell, `$env:PYTHONPATH = "src"` persists for the rest of that terminal
> session. Open a new terminal (or run `Remove-Item Env:\PYTHONPATH`) to clear it.

---

## 3. Run the demo

Both incidents run the **same** reasoning engine and reach **different** correct
root causes — that's the proof it reasons rather than replays a script.

```powershell
# Incident 1 — checkout 500s → root cause is a bad deploy (commit a3f9c21)
python -m sentinel --scenario checkout_500

# Incident 2 — API latency → root cause is infra (connection-pool exhaustion)
python -m sentinel --scenario api_latency_infra

# List available scenarios
python -m sentinel --list

# Write the postmortem to a specific file
python -m sentinel --scenario checkout_500 --out out/my-postmortem.md
```

Each run prints the live reasoning trace (PLAN → INVESTIGATE → SYNTHESIZE →
CRITIQUE) and writes a blameless postmortem to `out/<INCIDENT-ID>.postmortem.md`.

### Optional: colorized trace

```powershell
pip install rich
```

`rich` is auto-detected. Without it, the trace prints in plain text — same
content, no color.

---

## 4. Run the tests

The suite verifies both scenarios reach their correct, distinct root causes
(mock mode, no network).

```powershell
# With Setup A (editable install):
python -m pytest -q

# Or run the test file directly with Setup B:
$env:PYTHONPATH = "src"; python tests/test_pipeline.py
```

Expected: `2 passed`, or `ok: both scenarios reason to the correct, distinct
root causes`.

---

## 5. Verify it worked

After a run you should see:

- A green `✅ SENTINEL VERDICT` panel naming commit **a3f9c21** (for
  `checkout_500`) at ~97% confidence.
- A postmortem file in `out/`:

```powershell
Get-ChildItem out\           # list generated postmortems
Get-Content out\INC-4471.postmortem.md   # checkout_500 postmortem
```

---

## 6. Reproduce the underlying incident (optional)

A tiny Flask app that breaks on cue, mirroring commit `a3f9c21`:

```powershell
pip install flask
python sample_app/app.py                          # healthy: checkout returns 200
$env:CHECKOUT_VERSION = "buggy"; python sample_app/app.py   # reproduces the 500s
```

---

## 7. Live mode (real Foundry + MCP — needs keys)

Mock mode is the demo. Live mode runs the agents as a Microsoft Agent Framework
workflow on a Foundry deployment with live Azure/GitHub MCP servers.

```powershell
pip install -e ".[live]"      # installs agent-framework, openai, azure-identity, mcp, otel, rich
Copy-Item .env.example .env   # then fill in Foundry + Azure + GitHub values
python -m sentinel --mode live --scenario checkout_500
```

---

## 8. Troubleshooting

| Symptom | Fix |
|---|---|
| `No module named sentinel` | You skipped setup. Run `python -m pip install -e .` (Setup A) **or** prefix with `PYTHONPATH`/`$env:PYTHONPATH = "src"` (Setup B). |
| `Scenario not found: <name>` | Run `python -m sentinel --list` for valid names. Run from the repo root so `scenarios/` is found. |
| Trace prints with no color | Optional — `pip install rich`. |
| `WARNING: script sentinel.exe is not on PATH` | Harmless. Use `python -m sentinel` (the documented form) instead of the bare `sentinel` command. |
| Garbled box-drawing characters on Windows | Console glyphs are forced to UTF-8 in `tracing.py`; if your terminal still mangles them, switch to Windows Terminal or a UTF-8 codepage (`chcp 65001`). |
