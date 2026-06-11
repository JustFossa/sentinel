"""Sentinel orchestrator — the reasoning engine.

Drives the full RCA loop:

    PLAN  ──▶  INVESTIGATE (fan-out)  ──▶  SYNTHESIZE  ──▶  CRITIQUE
                                               ▲                │
                                               └─ targeted ◀────┘
                                                  follow-up (self-correction)

In LIVE mode the same agents are composed as a Microsoft Agent Framework
workflow (see maf_workflow.py) and run on a Foundry reasoning deployment; the
control flow below is the reference implementation that also powers the offline
demo. Keeping one engine means the demo and production reason identically.
"""

from __future__ import annotations

from .agents.critic import Critic
from .agents.investigators import CodeInvestigator, InfraInvestigator, LogInvestigator
from .agents.planner import Planner
from .agents.postmortem import PostmortemWriter
from .agents.synthesizer import Synthesizer
from .config import Config
from .models import IncidentAlert, IncidentResolution
from .tracing import ConsoleTracer

MAX_PASSES = 3


class SentinelOrchestrator:
    def __init__(self, cfg: Config, tracer: ConsoleTracer | None = None) -> None:
        self.cfg = cfg
        self.tracer = tracer or ConsoleTracer(cfg.otlp_endpoint)
        self.llm = self._make_llm()

    def _make_llm(self):
        if not self.cfg.is_live:
            return None
        try:
            from .llm import FoundryChatClient
            return FoundryChatClient(self.cfg)
        except Exception as exc:  # pragma: no cover
            self.tracer.note(f"Foundry client unavailable ({exc}); running without LLM narration.")
            return None

    def run(self, alert: IncidentAlert, scenario: dict) -> IncidentResolution:
        # Make scenario visible to the (mock) tool backends.
        self.cfg._scenario = scenario  # type: ignore[attr-defined]
        board: dict = {}
        t = self.tracer

        planner = Planner(self.cfg, self.llm)
        log = LogInvestigator(self.cfg, self.llm)
        code = CodeInvestigator(self.cfg, self.llm)
        infra = InfraInvestigator(self.cfg, self.llm)
        synth = Synthesizer(self.cfg, self.llm)
        critic = Critic(self.cfg, self.llm)
        scribe = PostmortemWriter(self.cfg, self.llm)

        t.panel("SENTINEL", f"Incident received\n{alert.as_prompt()}")

        # 1) PLAN -------------------------------------------------------- #
        t.stage("1 · PLAN — decompose into competing hypotheses")
        hyps = planner.plan(alert, t)

        # 2) INVESTIGATE (fan-out) -------------------------------------- #
        t.stage("2 · INVESTIGATE — specialist agents gather evidence in parallel")
        log_rep = log.investigate(alert, hyps, t, board)
        code_rep = code.investigate(alert, hyps, t, board)
        infra_rep = infra.investigate(alert, hyps, t, board)
        reports = [log_rep, code_rep, infra_rep]

        # 3) SYNTHESIZE ⇄ CRITIQUE (self-correction loop) --------------- #
        root_cause = None
        for p in range(1, MAX_PASSES + 1):
            t.stage(f"3 · SYNTHESIZE — eliminate hypotheses (pass {p})")
            root_cause = synth.synthesize(alert, hyps, reports, board, t)

            t.stage(f"4 · CRITIQUE — adversarial self-review (pass {p})")
            verdict = critic.review(alert, root_cause, board, p, t)
            if verdict.approved:
                break
            if "LogInvestigator.verify_onset" in verdict.followups:
                ev = log.verify_onset(alert, t, board)
                log_rep.evidence.append(ev)
                board["onset_verified"] = True
                continue
            break  # refuted / inconclusive — stop looping

        # 5) POSTMORTEM ------------------------------------------------- #
        t.stage("5 · REPORT — author postmortem")
        postmortem = scribe.write(alert, hyps, root_cause, board, t)

        self._final_panel(root_cause)
        return IncidentResolution(
            alert=alert, hypotheses=hyps, reports=reports,
            root_cause=root_cause, postmortem_markdown=postmortem,
        )

    def _final_panel(self, rc) -> None:
        body = (
            f"ROOT CAUSE  ({rc.confidence:.0%} confidence)\n"
            f"{rc.summary}\n\n"
            f"OFFENDING CHANGE\n{rc.offending_change or 'n/a'}\n\n"
            f"RECOMMENDED ACTION\n{rc.recommended_action}"
        )
        self.tracer.panel("✅ SENTINEL VERDICT", body)
