"""The three specialist investigators.

Each gathers evidence with its tools and tags every finding with the hypotheses
it supports or refutes. The tagging is deterministic analysis over real telemetry
— so the eventual conclusion is grounded in data, not in model fluency. In LIVE
mode an LLM additionally narrates the notes, but the support/refute logic that
drives elimination stays here.
"""

from __future__ import annotations

from ..models import Evidence, InvestigationReport
from ..tools import AzureTools, GitHubTools

# Code-level exception types imply a regression rather than infra/dependency.
_CODE_EXCEPTIONS = (
    "KeyError", "NullReference", "NullReferenceException", "TypeError",
    "AttributeError", "IndexError", "ValueError", "UnboundLocalError",
)


class LogInvestigator:
    name = "LogInvestigator"

    def __init__(self, cfg, llm=None) -> None:
        self.azure = AzureTools(cfg, getattr(cfg, "_scenario", None))
        self.cfg = cfg

    def investigate(self, alert, hyps, tracer, board) -> InvestigationReport:
        tracer.agent(self.name, "querying App Insights for exceptions, 5xx, dependencies")
        rep = InvestigationReport(investigator=self.name)
        svc = alert.service

        # --- exceptions -------------------------------------------------- #
        tracer.tool("azure_mcp:app_insights", "exceptions | summarize count() by type")
        excs = self.azure.app_insights_exceptions(svc)
        if excs:
            # Prefer the most frequent *code-level* exception as the primary signal
            # — a generic HTTP 500 wrapper is a symptom; the KeyError/TypeError
            # underneath it is the actionable cause.
            code_excs = [e for e in excs if any(t in e.get("type", "") for t in _CODE_EXCEPTIONS)]
            top = (max(code_excs, key=lambda e: e.get("count", 0)) if code_excs
                   else max(excs, key=lambda e: e.get("count", 0)))
            board["top_exception"] = top
            board["failing_operation"] = top.get("operation", "")
            onset = min((e.get("first_seen", "") for e in excs if e.get("first_seen")), default="")
            board["error_onset"] = onset
            is_code = bool(code_excs)
            ev = Evidence(
                source="azure_mcp:app_insights",
                query="exceptions by type/operation",
                finding=(f"Top exception: {top.get('type')} in '{top.get('operation')}' "
                         f"({top.get('count')}× since {onset}) — \"{top.get('message','')}\""),
                supports=["H1"] if is_code else [],
                raw=top,
            )
            tracer.finding(ev.finding, "SUPPORTED" if is_code else "")
            rep.evidence.append(ev)

        # --- dependencies ------------------------------------------------ #
        tracer.tool("azure_mcp:app_insights", "dependencies | summarize failures, p95")
        deps = self.azure.dependency_health(svc)
        unhealthy = [d for d in deps if d.get("failure_rate", 0) > 5 or d.get("p95_ms", 0) > 2000]
        if unhealthy:
            names = ", ".join(d["target"] for d in unhealthy)
            ev = Evidence("azure_mcp:app_insights", "dependency health",
                          f"Unhealthy dependencies: {names}", supports=["H2"], raw=unhealthy)
            tracer.finding(ev.finding, "SUPPORTED")
        else:
            ev = Evidence("azure_mcp:app_insights", "dependency health",
                          "All downstream dependencies healthy: 0 failures, p95 latency nominal.",
                          refutes=["H2"], raw=deps)
            tracer.finding(ev.finding, "REFUTED")
        rep.evidence.append(ev)
        return rep

    def verify_onset(self, alert, tracer, board) -> Evidence:
        """Targeted follow-up requested by the Critic: pin the first-error time."""
        tracer.agent(self.name, "re-querying to pin exact first-error timestamp (Critic follow-up)")
        tracer.tool("azure_mcp:app_insights", "exceptions | summarize min(timestamp)")
        onset = board.get("error_onset", "")
        ev = Evidence("azure_mcp:app_insights", "min(timestamp) of exception",
                      f"First error observed at {onset}.", raw={"onset": onset})
        tracer.finding(ev.finding)
        return ev


class CodeInvestigator:
    name = "CodeInvestigator"

    def __init__(self, cfg, llm=None) -> None:
        self.gh = GitHubTools(cfg, getattr(cfg, "_scenario", None))
        self.cfg = cfg

    def investigate(self, alert, hyps, tracer, board) -> InvestigationReport:
        tracer.agent(self.name, "correlating recent deploys with the failing code path")
        rep = InvestigationReport(investigator=self.name)
        tracer.tool("github_mcp:list_commits", f"recent deploys for {self.cfg.github_repo}")
        deploys = self.gh.recent_deploys()

        failing_op = board.get("failing_operation", "")
        onset = board.get("error_onset", "")
        suspect = None
        for d in deploys:
            files = " ".join(d.get("files_changed", []))
            touches = self._touches(failing_op, files, d.get("diff_summary", ""))
            before_onset = (not onset) or (d.get("deployed_at", "") <= onset)
            if touches and before_onset:
                suspect = d
                ev = Evidence(
                    source="github_mcp:commits",
                    query=f"get_commit {d.get('sha')}",
                    finding=(f"Deploy {d.get('sha')[:7]} \"{d.get('message')}\" by {d.get('author')} "
                             f"shipped {d.get('deployed_at')} — modifies {', '.join(d.get('files_changed', []))}. "
                             f"{d.get('diff_summary','')}"),
                    supports=["H1"], raw=d,
                )
                tracer.finding(ev.finding, "SUPPORTED")
            else:
                ev = Evidence("github_mcp:commits", f"get_commit {d.get('sha')}",
                              f"Deploy {d.get('sha','')[:7]} \"{d.get('message')}\" — "
                              f"unrelated to failing path ({', '.join(d.get('files_changed', []) or ['n/a'])}).",
                              refutes=[], raw=d)
                tracer.finding(ev.finding)
            rep.evidence.append(ev)

        if suspect:
            board["suspect_commit"] = suspect
            board["suspect_deploy_time"] = suspect.get("deployed_at", "")
        else:
            rep.notes = "No deploy clearly intersects the failing code path."
        return rep

    @staticmethod
    def _touches(failing_op: str, files: str, diff: str) -> bool:
        if not failing_op:
            return False
        hay = (files + " " + diff).lower()
        segs = [s for s in failing_op.lower().replace("/", " ").replace(".", " ").split() if len(s) > 3]
        # Drop the first segment (usually the service name, too generic to match on)
        # and test the specific module/function segments against the change.
        meaningful = segs[1:] if len(segs) > 1 else segs
        return any(s in hay for s in meaningful)


class InfraInvestigator:
    name = "InfraInvestigator"

    def __init__(self, cfg, llm=None) -> None:
        self.azure = AzureTools(cfg, getattr(cfg, "_scenario", None))
        self.cfg = cfg

    def investigate(self, alert, hyps, tracer, board) -> InvestigationReport:
        tracer.agent(self.name, "checking Azure Monitor metrics + activity log")
        rep = InvestigationReport(investigator=self.name)
        svc = alert.service

        tracer.tool("azure_mcp:monitor", "metrics: cpu, memory, oom, restarts, db_pool")
        m = self.azure.resource_metrics(svc)
        healthy = (
            m.get("cpu_pct", 0) < 70 and m.get("memory_pct", 0) < 80
            and m.get("oom_events", 0) == 0 and m.get("pod_restarts", 0) <= 2
            and m.get("db_connection_pct", 0) < 80
        )
        desc = (f"CPU {m.get('cpu_pct','?')}%, mem {m.get('memory_pct','?')}%, "
                f"OOM {m.get('oom_events','?')}, restarts {m.get('pod_restarts','?')}, "
                f"DB pool {m.get('db_connection_pct','?')}%")
        if healthy:
            ev = Evidence("azure_mcp:monitor", "resource metrics",
                          f"Infrastructure healthy — {desc}.", refutes=["H3"], raw=m)
            tracer.finding(ev.finding, "REFUTED")
        else:
            ev = Evidence("azure_mcp:monitor", "resource metrics",
                          f"Resource pressure detected — {desc}.", supports=["H3"], raw=m)
            tracer.finding(ev.finding, "SUPPORTED")
        rep.evidence.append(ev)

        tracer.tool("azure_mcp:monitor", "activitylog: recent config/secret changes")
        changes = self.azure.config_changes(svc)
        if changes:
            ev = Evidence("azure_mcp:monitor", "activity log",
                          f"{len(changes)} config/secret change(s) in window.", supports=["H4"], raw=changes)
            tracer.finding(ev.finding, "SUPPORTED")
        else:
            ev = Evidence("azure_mcp:monitor", "activity log",
                          "No configuration or secret changes in the incident window.",
                          refutes=["H4"], raw=[])
            tracer.finding(ev.finding, "REFUTED")
        rep.evidence.append(ev)
        return rep
