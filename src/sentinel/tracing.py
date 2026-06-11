"""Reasoning trace.

Every stage of Sentinel's reasoning emits a trace event. The ConsoleTracer
renders it for the demo; in LIVE mode the same events also become OpenTelemetry
spans so they show up in the Foundry Control Plane next to model + tool calls.
That single trace view *is* the architecture diagram judges see at runtime.
"""

from __future__ import annotations

import sys
import time
from typing import Any


def _force_utf8_stdio() -> None:
    """Make the reasoning trace printable on a stock Windows console.

    Windows terminals default to a legacy code page (cp1252) that can't encode
    the trace glyphs (▸ ⛁ ✓ ✗ ══ •), which crashes both the rich renderer and
    the stdlib `print` fallback. Reconfiguring stdio to UTF-8 fixes both paths;
    `errors="replace"` keeps the demo running even on a stream that still can't.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[union-attr]
        except (AttributeError, ValueError):
            pass  # already-UTF-8, redirected, or non-reconfigurable stream


_force_utf8_stdio()

try:                                # pretty output if rich is present
    from rich.console import Console
    from rich.panel import Panel
    from rich.tree import Tree
    _RICH = True
    _console = Console()
except Exception:                   # stdlib fallback — demo still runs
    _RICH = False
    _console = None


_AGENT_COLORS = {
    "Orchestrator": "bold white",
    "Planner": "bold magenta",
    "LogInvestigator": "cyan",
    "CodeInvestigator": "green",
    "InfraInvestigator": "yellow",
    "Synthesizer": "bold blue",
    "Critic": "bold red",
    "Postmortem": "bold white",
}


class ConsoleTracer:
    """Human-readable, step-by-step trace of the agents' reasoning."""

    def __init__(self, otlp_endpoint: str = "") -> None:
        self.otlp_endpoint = otlp_endpoint
        self._otel = self._init_otel(otlp_endpoint) if otlp_endpoint else None

    # -- public API -------------------------------------------------------- #
    def stage(self, title: str) -> None:
        line = f"\n══════ {title} ══════"
        _console.rule(f"[bold]{title}") if _RICH else print(line)

    def agent(self, name: str, action: str) -> None:
        color = _AGENT_COLORS.get(name, "white")
        if _RICH:
            _console.print(f"[{color}]▸ {name}[/]: {action}")
        else:
            print(f"  ▸ {name}: {action}")
        self._span(f"{name}.{action[:40]}")

    def tool(self, server: str, call: str) -> None:
        if _RICH:
            _console.print(f"   [dim]⛁ {server} → {call}[/]")
        else:
            print(f"     ⛁ {server} → {call}")

    def finding(self, text: str, verdict: str = "") -> None:
        mark = {"CONFIRMED": "✓", "REFUTED": "✗", "SUPPORTED": "•",
                "INCONCLUSIVE": "?"}.get(verdict, "–")
        if _RICH:
            color = {"CONFIRMED": "green", "REFUTED": "red",
                     "SUPPORTED": "yellow"}.get(verdict, "white")
            _console.print(f"     [{color}]{mark}[/] {text}")
        else:
            print(f"       {mark} {text}")

    def note(self, text: str) -> None:
        _console.print(f"   [italic dim]{text}[/]") if _RICH else print(f"     … {text}")

    def panel(self, title: str, body: str) -> None:
        if _RICH:
            _console.print(Panel(body, title=title, border_style="bold green"))
        else:
            print(f"\n--- {title} ---\n{body}\n")

    # -- OpenTelemetry (live) --------------------------------------------- #
    def _init_otel(self, endpoint: str) -> Any:
        try:
            from opentelemetry import trace
            from opentelemetry.sdk.resources import Resource
            from opentelemetry.sdk.trace import TracerProvider
            from opentelemetry.sdk.trace.export import BatchSpanProcessor
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import (
                OTLPSpanExporter,
            )

            provider = TracerProvider(resource=Resource.create({"service.name": "sentinel-rca"}))
            provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter(endpoint=endpoint)))
            trace.set_tracer_provider(provider)
            return trace.get_tracer("sentinel")
        except Exception:
            return None

    def _span(self, name: str) -> None:
        if not self._otel:
            return
        with self._otel.start_as_current_span(name):
            time.sleep(0)  # marker span; real spans wrap model/tool calls in live agents
