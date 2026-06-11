"""Synthesizer agent — eliminates hypotheses and names the root cause.

Tallies every investigator's support/refute tags per hypothesis, eliminates the
refuted ones, and elevates the surviving supported hypothesis to a root cause.
This is deductive elimination ("once you eliminate the impossible…"), the core
of credible RCA — and it runs identically in mock and live.
"""

from __future__ import annotations

from ..models import Evidence, Hypothesis, InvestigationReport, RootCause, Verdict


class Synthesizer:
    name = "Synthesizer"

    def __init__(self, cfg, llm=None) -> None:
        self.cfg = cfg
        self.llm = llm

    def synthesize(
        self,
        alert,
        hyps: list[Hypothesis],
        reports: list[InvestigationReport],
        board: dict,
        tracer,
    ) -> RootCause:
        tracer.agent(self.name, "tallying evidence and eliminating hypotheses")
        all_ev: list[Evidence] = [e for r in reports for e in r.evidence]

        # tally support / refute per hypothesis
        for h in hyps:
            sup = [e for e in all_ev if h.id in e.supports]
            ref = [e for e in all_ev if h.id in e.refutes]
            if ref and not sup:
                h.verdict, h.confidence = Verdict.REFUTED, 0.9
            elif sup and not ref:
                h.verdict = Verdict.SUPPORTED
                h.confidence = min(0.6 + 0.15 * len(sup), 0.9)
            elif sup and ref:
                h.verdict, h.confidence = Verdict.INCONCLUSIVE, 0.4
            else:
                h.verdict, h.confidence = Verdict.INCONCLUSIVE, 0.2
            tracer.finding(f"{h.id} [{h.category}] → {h.verdict.value} ({h.confidence:.2f})",
                           h.verdict.value)

        supported = [h for h in hyps if h.verdict == Verdict.SUPPORTED]
        eliminated = [h for h in hyps if h.verdict == Verdict.REFUTED]
        winner = max(supported, key=lambda h: h.confidence, default=None)

        suspect = board.get("suspect_commit")
        top_exc = board.get("top_exception", {})

        if winner is None:
            summary = "Evidence is inconclusive; no single hypothesis survived elimination."
            return RootCause(summary=summary, offending_change=None, confidence=0.3,
                             eliminated=[h.statement for h in eliminated])

        # confidence: base + corroboration
        conf = winner.confidence
        if suspect:
            conf = min(conf + 0.2, 0.95)
        if len(supported) == 1 and eliminated:
            conf = min(conf + 0.1, 0.97)

        offending = None
        if suspect:
            offending = f"{suspect.get('sha','')[:7]} \"{suspect.get('message','')}\" by {suspect.get('author','')}"
            summary = (
                f"{winner.category.upper()} regression: deploy {offending} altered "
                f"'{board.get('failing_operation','the failing path')}', triggering "
                f"{top_exc.get('type','an exception')} (\"{top_exc.get('message','')}\") "
                f"and the {alert.signals.get('error_rate','elevated')} rate on {alert.service}."
            )
            action = (
                f"Roll back deploy {suspect.get('sha','')[:7]} immediately to restore service, "
                f"then ship a forward-fix that restores the removed safeguard in "
                f"{', '.join(suspect.get('files_changed', [])) or 'the affected module'}."
            )
        else:
            summary = f"{winner.statement} (supported by direct evidence; no code change implicated)."
            if winner.category == "infra":
                action = ("Relieve resource pressure now (scale out / raise the connection-pool "
                          "limit), then add an autoscale rule and a saturation alert.")
            elif winner.category == "dependency":
                action = ("Fail over or throttle the unhealthy dependency, then open an incident "
                          "with its owning team.")
            elif winner.category == "config":
                action = "Revert the recent configuration/secret change and add a validation gate."
            else:
                action = "Mitigate per runbook; continue investigation to localize the change."

        supporting = [e.finding for e in all_ev if winner.id in e.supports]
        rc = RootCause(
            summary=summary,
            offending_change=offending,
            confidence=conf,
            supporting_evidence=supporting,
            eliminated=[f"{h.id} {h.statement}" for h in eliminated],
            recommended_action=action,
        )

        # LIVE: let the reasoning model phrase the summary more naturally.
        if self.cfg.is_live and self.llm is not None:
            try:
                rc.summary = self.llm.complete(
                    "Rewrite this root-cause summary in 2 crisp sentences for an on-call engineer.",
                    summary,
                ) or summary
            except Exception:
                pass

        tracer.note(f"Winner: {winner.id} ({winner.category}) — provisional confidence {conf:.2f}")
        return rc
