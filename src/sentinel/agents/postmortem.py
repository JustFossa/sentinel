"""Postmortem writer — turns the verified reasoning into a shareable doc.

Produces a blameless postmortem (timeline, root cause, impact, resolution,
action items) an on-call engineer can paste into the incident channel. Template
in mock mode; reasoning-model-authored in live mode.
"""

from __future__ import annotations

from datetime import datetime


class PostmortemWriter:
    name = "Postmortem"

    def __init__(self, cfg, llm=None) -> None:
        self.cfg = cfg
        self.llm = llm

    def write(self, alert, hyps, root_cause, board, tracer) -> str:
        tracer.agent(self.name, "drafting blameless postmortem")
        suspect = board.get("suspect_commit", {})
        top = board.get("top_exception", {})
        elim = "\n".join(f"- ~~{e}~~ — refuted by direct evidence" for e in root_cause.eliminated)
        support = "\n".join(f"- {s}" for s in root_cause.supporting_evidence)

        # Timeline: only show deploy rows when a code change is actually implicated.
        rows: list[str] = []
        if suspect:
            rows.append(f'| {suspect.get("merged_at","—")} | PR merged: "{suspect.get("message","—")}" |')
            rows.append(f'| {suspect.get("deployed_at","—")} | Deploy reached production |')
        if board.get("error_onset"):
            rows.append(f'| {board["error_onset"]} | First errors observed in `{board.get("failing_operation","")}` |')
        rows.append(f'| {alert.fired_at} | Alert fired ({alert.signals.get("error_rate","")}) |')
        timeline = "\n".join(rows)

        # Action items adapt to whether there's an offending change to roll back.
        fix_item = ("Roll back / forward-fix the offending change"
                    if root_cause.offending_change
                    else "Apply the mitigation above and confirm recovery")
        guard_item = (f"Add a deploy-gate alert on 5xx rate for `{alert.service}`"
                      if root_cause.offending_change
                      else f"Add a saturation/health alert for `{alert.service}`")

        md = f"""# Postmortem — {alert.title}

**Incident:** {alert.id}  |  **Service:** {alert.service}  |  **Severity:** {alert.severity}
**Detected:** {alert.fired_at}  |  **Authored by:** Sentinel (autonomous RCA agent)
**Confidence:** {root_cause.confidence:.0%}

## Summary
{root_cause.summary}

## Impact
{alert.summary}

## Root Cause
{root_cause.summary}

**Offending change:** `{root_cause.offending_change or 'n/a'}`
**Failing path:** `{board.get('failing_operation', 'n/a')}`
**Primary symptom:** {top.get('type','n/a')} — "{top.get('message','')}"

## Timeline
| Time | Event |
|------|-------|
{timeline}

## Evidence (supporting)
{support or '- (none)'}

## Hypotheses eliminated
{elim or '- (none)'}

## Resolution / Recommended action
{root_cause.recommended_action}

## Self-critique (agent)
{root_cause.self_critique}

## Action items
- [ ] {fix_item}
- [ ] Add a regression test for `{board.get('failing_operation','the failing path')}`
- [ ] {guard_item}

---
*Generated automatically by Sentinel. Review before closing the incident.*
"""
        if self.cfg.is_live and self.llm is not None:
            try:
                md = self.llm.complete(
                    "You are an SRE writing a concise blameless postmortem. Improve clarity; "
                    "keep all facts, the table, and the markdown structure.",
                    md,
                ) or md
            except Exception:
                pass

        tracer.note(f"Postmortem drafted ({len(md.splitlines())} lines).")
        return md
