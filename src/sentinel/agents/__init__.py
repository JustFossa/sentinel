"""Sentinel's specialist agents.

In LIVE mode each of these is a Microsoft Agent Framework ChatAgent with its own
system prompt and bound MCP tools, orchestrated by a MAF workflow. In MOCK mode
the same classes run their deterministic analytical core directly. Either way the
reasoning artifacts (Hypothesis / Evidence / RootCause) are identical.
"""
