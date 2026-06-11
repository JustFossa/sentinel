"""Domain tools the investigators call.

Each tool has two backends:
  * MOCK  — reads the canned incident scenario (offline, deterministic demo).
  * LIVE  — calls a real MCP server (Azure MCP for telemetry, GitHub MCP for
            deploy/PR data) via mcp_client.

Investigators don't care which backend is active; they just call the methods.
This is what lets the *exact same reasoning* run in the demo and in production.
"""

from __future__ import annotations

from typing import Any

from .config import Config


# --------------------------------------------------------------------------- #
#  Azure MCP — telemetry, metrics, resource health, config/activity log
# --------------------------------------------------------------------------- #
class AzureTools:
    server = "azure_mcp"

    def __init__(self, cfg: Config, scenario: dict[str, Any] | None = None) -> None:
        self.cfg = cfg
        self.scenario = scenario or {}

    # --- App Insights exceptions (KQL via Azure Monitor tools) ------------- #
    def app_insights_exceptions(self, service: str, window_min: int = 30) -> list[dict]:
        if self.cfg.is_live:
            kql = (
                f"exceptions | where cloud_RoleName == '{service}' "
                f"| where timestamp > ago({window_min}m) "
                f"| summarize count() by type, outerMessage, operation_Name "
                f"| order by count_ desc"
            )
            return self._live_kql(kql)
        return self.scenario.get("telemetry", {}).get("exceptions", [])

    # --- 5xx error-rate series --------------------------------------------- #
    def http_5xx_series(self, service: str, window_min: int = 30) -> list[dict]:
        if self.cfg.is_live:
            kql = (
                f"requests | where cloud_RoleName == '{service}' "
                f"| where timestamp > ago({window_min}m) "
                f"| summarize total=count(), errors=countif(resultCode >= 500) "
                f"by bin(timestamp, 1m) | order by timestamp asc"
            )
            return self._live_kql(kql)
        return self.scenario.get("telemetry", {}).get("http_5xx", [])

    # --- Downstream dependency health -------------------------------------- #
    def dependency_health(self, service: str, window_min: int = 30) -> list[dict]:
        if self.cfg.is_live:
            kql = (
                f"dependencies | where cloud_RoleName == '{service}' "
                f"| where timestamp > ago({window_min}m) "
                f"| summarize calls=count(), failures=countif(success==false), "
                f"p95=percentile(duration,95) by target | order by failures desc"
            )
            return self._live_kql(kql)
        return self.scenario.get("telemetry", {}).get("dependencies", [])

    # --- Azure Monitor resource metrics ------------------------------------ #
    def resource_metrics(self, service: str) -> dict:
        if self.cfg.is_live:
            return self._live_tool(
                "azmcp-monitor-metrics-query",
                {"subscription": self.cfg.azure_subscription_id, "resource": service},
            ) or {}
        return self.scenario.get("metrics", {})

    # --- Azure activity log: recent config / secret changes ---------------- #
    def config_changes(self, service: str, window_min: int = 60) -> list[dict]:
        if self.cfg.is_live:
            return self._live_tool(
                "azmcp-monitor-activitylog-query",
                {"subscription": self.cfg.azure_subscription_id, "resource": service,
                 "window": f"{window_min}m"},
            ) or []
        return self.scenario.get("config_changes", [])

    # --- live helpers ------------------------------------------------------ #
    def _live_kql(self, kql: str) -> Any:
        # Azure MCP exposes Log Analytics / App Insights querying through its
        # monitor tools. Tool name can vary by version; adjust to your install.
        from . import mcp_client

        return mcp_client.stdio_call(
            self.cfg.azure_mcp_command, self.cfg.azure_mcp_args,
            "azmcp-monitor-log-query",
            {"subscription": self.cfg.azure_subscription_id, "query": kql},
        )

    def _live_tool(self, name: str, args: dict) -> Any:
        from . import mcp_client

        return mcp_client.stdio_call(
            self.cfg.azure_mcp_command, self.cfg.azure_mcp_args, name, args
        )


# --------------------------------------------------------------------------- #
#  GitHub MCP — recent deploys / commits / diffs
# --------------------------------------------------------------------------- #
class GitHubTools:
    server = "github_mcp"

    def __init__(self, cfg: Config, scenario: dict[str, Any] | None = None) -> None:
        self.cfg = cfg
        self.scenario = scenario or {}

    def recent_deploys(self, repo: str | None = None, since_min: int = 120) -> list[dict]:
        if self.cfg.is_live:
            owner, _, name = (repo or self.cfg.github_repo).partition("/")
            commits = self._live_tool("list_commits", {"owner": owner, "repo": name}) or []
            return commits
        return self.scenario.get("deploys", [])

    def get_commit(self, sha: str, repo: str | None = None) -> dict:
        if self.cfg.is_live:
            owner, _, name = (repo or self.cfg.github_repo).partition("/")
            return self._live_tool("get_commit", {"owner": owner, "repo": name, "sha": sha}) or {}
        for d in self.scenario.get("deploys", []):
            if d.get("sha") == sha:
                return d
        return {}

    def _live_tool(self, name: str, args: dict) -> Any:
        from . import mcp_client

        headers = {"Authorization": f"Bearer {self.cfg.github_token}"}
        return mcp_client.http_call(self.cfg.github_mcp_url, headers, name, args)


# --------------------------------------------------------------------------- #
#  Runbooks — institutional knowledge (mock: scenario; live: your wiki/MCP)
# --------------------------------------------------------------------------- #
class RunbookTools:
    def __init__(self, cfg: Config, scenario: dict[str, Any] | None = None) -> None:
        self.cfg = cfg
        self.scenario = scenario or {}

    def lookup(self, service: str, symptom: str) -> list[dict]:
        books = self.scenario.get("runbooks", [])
        hits = [b for b in books if b.get("service") == service]
        return hits or books
