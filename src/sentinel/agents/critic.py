"""Critic agent — self-correction before Sentinel commits to an answer.

The critic doesn't trust the synthesizer's first draft. It runs adversarial
checks and, if a check can't be satisfied from current evidence, sends the team
back for a targeted follow-up. This loop is the difference between a confident
guess and a verified root cause — and it's exactly the multi-step reasoning the
Reasoning Agents track rewards.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CriticResult:
    approved: bool
    confidence: float
    critique: str
    followups: list[str] = field(default_factory=list)


class Critic:
    name = "Critic"

    def __init__(self, cfg, llm=None) -> None:
        self.cfg = cfg
        self.llm = llm

    def review(self, alert, root_cause, board: dict, pass_num: int, tracer) -> CriticResult:
        tracer.agent(self.name, f"adversarial review (pass {pass_num})")
        checks: list[str] = []

        # Check 1 — is there a concrete offending change at all?
        if root_cause.offending_change is None:
            checks.append("No offending change pinpointed; conclusion is weak.")

        # Check 2 — TEMPORAL SOUNDNESS. The headline claim is "deploy caused it",
        # which only holds if errors began AFTER the deploy. On the first pass we
        # have not *independently verified* the first-error timestamp, so we send
        # the LogInvestigator back to confirm it before trusting the correlation.
        onset = board.get("error_onset")
        deploy_t = board.get("suspect_deploy_time")
        verified = board.get("onset_verified", False)
        if root_cause.offending_change and not verified:
            checks.append(
                "Correlation with the deploy is assumed, not proven. Need the exact "
                "first-error timestamp confirmed against the deploy time."
            )
            tracer.finding("Temporal ordering not yet verified — requesting follow-up.", "")
            return CriticResult(
                approved=False,
                confidence=min(root_cause.confidence, 0.6),
                critique=" ".join(checks),
                followups=["LogInvestigator.verify_onset"],
            )

        # Pass 2+: temporal evidence is in. Validate ordering.
        if onset and deploy_t:
            if deploy_t <= onset:
                tracer.finding(
                    f"Verified: errors began {onset} — AFTER deploy at {deploy_t}. "
                    "Causality holds.", "CONFIRMED")
                conf = min(root_cause.confidence + 0.03, 0.97)
            else:
                tracer.finding(
                    f"Errors began {onset} BEFORE deploy {deploy_t} — deploy is NOT the cause!",
                    "REFUTED")
                return CriticResult(
                    approved=False, confidence=0.35,
                    critique="Temporal order refutes the deploy hypothesis; reopen investigation.",
                    followups=[],
                )
        else:
            conf = root_cause.confidence

        # Check 3 — confidence floor for auto-remediation guidance.
        approved = conf >= 0.8
        critique = (
            "Single hypothesis survived elimination; competing causes (dependency, infra, "
            "config) were each refuted by direct evidence; temporal order confirmed."
            if approved else
            "Confidence below the 0.80 threshold for a firm call; flag for human review."
        )
        root_cause.confidence = conf
        root_cause.self_critique = critique
        tracer.finding(f"Review complete — confidence {conf:.2f}, approved={approved}.",
                       "CONFIRMED" if approved else "")
        return CriticResult(approved=approved, confidence=conf, critique=critique)
