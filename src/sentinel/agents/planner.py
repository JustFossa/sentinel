"""Planner agent — decomposes the incident into testable hypotheses.

This is the first reasoning step: rather than guessing a cause, the planner
enumerates the *competing* explanations that must be tested and assigns each to
the investigator best equipped to gather evidence for it. Good triage = good RCA.
"""

from __future__ import annotations

from ..models import Hypothesis, IncidentAlert

SYSTEM = """You are the Planner in an incident root-cause analysis team.
Given an incident alert, enumerate the 3-5 most likely *competing* root-cause
hypotheses. Categories: deploy, dependency, infra, config, data. For each, give
a one-line statement, the category, a short rationale, and which investigator
should test it (LogInvestigator, CodeInvestigator, or InfraInvestigator).
Return JSON: {"hypotheses":[{"id","statement","category","rationale","assigned_to"}]}"""


def _standard_set(alert: IncidentAlert) -> list[Hypothesis]:
    s = alert.service
    return [
        Hypothesis(
            id="H1",
            statement=f"A recent code deployment introduced a regression in {s}.",
            category="deploy",
            rationale="5xx spikes that begin abruptly most often correlate with a deploy.",
            assigned_to="CodeInvestigator",
        ),
        Hypothesis(
            id="H2",
            statement=f"A downstream dependency of {s} (DB, payment, cache) is failing or slow.",
            category="dependency",
            rationale="Cascading failures from dependencies present as 5xx with elevated latency.",
            assigned_to="LogInvestigator",
        ),
        Hypothesis(
            id="H3",
            statement=f"Resource exhaustion (CPU, memory, OOM, connection pool) is degrading {s}.",
            category="infra",
            rationale="Saturation produces timeouts and restarts that surface as 5xx.",
            assigned_to="InfraInvestigator",
        ),
        Hypothesis(
            id="H4",
            statement=f"A recent configuration or secret change broke {s}.",
            category="config",
            rationale="Rotated secrets or flipped flags can break a service with no code deploy.",
            assigned_to="InfraInvestigator",
        ),
    ]


class Planner:
    name = "Planner"

    def __init__(self, cfg, llm=None) -> None:
        self.cfg = cfg
        self.llm = llm

    def plan(self, alert: IncidentAlert, tracer) -> list[Hypothesis]:
        tracer.agent(self.name, "decomposing incident into competing hypotheses")
        if self.cfg.is_live and self.llm is not None:
            data = self.llm.complete_json(SYSTEM, alert.as_prompt())
            items = data.get("hypotheses") if isinstance(data, dict) else None
            if items:
                hyps = [
                    Hypothesis(
                        id=i.get("id", f"H{n+1}"),
                        statement=i["statement"],
                        category=i.get("category", "unknown"),
                        rationale=i.get("rationale", ""),
                        assigned_to=i.get("assigned_to", "LogInvestigator"),
                    )
                    for n, i in enumerate(items)
                ]
            else:
                hyps = _standard_set(alert)
        else:
            hyps = _standard_set(alert)

        for h in hyps:
            tracer.finding(f"{h.id} [{h.category}] {h.statement}  → {h.assigned_to}")
        return hyps
