"""Typed reasoning artifacts passed between agents.

These make the multi-step reasoning *legible*: the planner emits Hypotheses,
investigators attach Evidence, the synthesizer renders a Verdict per hypothesis,
and the critic produces a confidence-checked RootCause. This structure is what
the judges (and the OpenTelemetry trace) see.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Verdict(str, Enum):
    CONFIRMED = "CONFIRMED"
    REFUTED = "REFUTED"
    INCONCLUSIVE = "INCONCLUSIVE"
    SUPPORTED = "SUPPORTED"  # evidence leans for it, not yet conclusive


@dataclass
class IncidentAlert:
    """The triggering signal — e.g. from Azure Monitor / PagerDuty."""

    id: str
    service: str
    title: str
    severity: str
    fired_at: str
    summary: str
    signals: dict[str, Any] = field(default_factory=dict)

    def as_prompt(self) -> str:
        sig = ", ".join(f"{k}={v}" for k, v in self.signals.items())
        return (
            f"INCIDENT {self.id} [{self.severity}] on '{self.service}' at {self.fired_at}\n"
            f"{self.title}\n{self.summary}\nSignals: {sig}"
        )


@dataclass
class Hypothesis:
    """A candidate root cause the planner wants to test."""

    id: str
    statement: str
    category: str            # deploy | dependency | infra | config | data
    rationale: str
    assigned_to: str         # which investigator should test it
    verdict: Verdict = Verdict.INCONCLUSIVE
    confidence: float = 0.0


@dataclass
class Evidence:
    """A single fact gathered by an investigator via a tool."""

    source: str              # e.g. "azure_mcp:app_insights" | "github_mcp:commits"
    query: str               # the exact query/tool call made
    finding: str             # human-readable observation
    supports: list[str] = field(default_factory=list)   # hypothesis ids it supports
    refutes: list[str] = field(default_factory=list)     # hypothesis ids it refutes
    raw: Any = None          # raw tool payload (kept for the trace)


@dataclass
class InvestigationReport:
    """What one investigator concluded after running its tools."""

    investigator: str
    evidence: list[Evidence] = field(default_factory=list)
    notes: str = ""


@dataclass
class RootCause:
    """The synthesizer + critic's final, confidence-checked conclusion."""

    summary: str
    offending_change: str | None
    confidence: float
    supporting_evidence: list[str] = field(default_factory=list)
    eliminated: list[str] = field(default_factory=list)
    recommended_action: str = ""
    self_critique: str = ""


@dataclass
class IncidentResolution:
    """The full package Sentinel returns: the reasoning trail + the answer."""

    alert: IncidentAlert
    hypotheses: list[Hypothesis]
    reports: list[InvestigationReport]
    root_cause: RootCause
    postmortem_markdown: str = ""
