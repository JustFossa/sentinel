"""LIVE production wiring: compose Sentinel as a Microsoft Agent Framework workflow.

This is the path that runs on Microsoft Foundry. It builds one ChatAgent per role
on a Foundry reasoning deployment (GPT-5.2 / MAI-Thinking-1), binds the Azure MCP
and GitHub MCP tool servers, and orchestrates them with a concurrent fan-out
(investigators) into a Magentic-style manager (synthesizer + critic).

Notes
-----
* Requires `pip install "sentinel-rca[live]"` and a configured `.env`.
* Import paths target Microsoft Agent Framework >= 1.0 (GA, April 2026). If your
  installed MAF build differs, adjust the imports — the composition is unchanged.
* The offline demo does NOT use this module; see orchestrator.py for the engine
  that runs everywhere. This file shows judges the native Foundry/MAF integration.
"""

from __future__ import annotations

from .config import Config

PLANNER_PROMPT = (
    "You are the Planner in an incident RCA team. Decompose the alert into 3-5 "
    "competing, testable root-cause hypotheses (deploy/dependency/infra/config/data) "
    "and assign each to the right investigator."
)
LOG_PROMPT = (
    "You are the Log Investigator. Use the Azure MCP monitor tools to query App "
    "Insights for exceptions, 5xx rate and dependency health. Tag every finding "
    "with the hypotheses it supports or refutes. Never speculate beyond the data."
)
CODE_PROMPT = (
    "You are the Code Investigator. Use the GitHub MCP to list recent deploys and "
    "inspect commits. Identify any deploy whose diff intersects the failing code "
    "path and shipped just before error onset."
)
INFRA_PROMPT = (
    "You are the Infra Investigator. Use Azure MCP to read Azure Monitor metrics "
    "and the activity log. Determine whether resource pressure or a config/secret "
    "change could explain the incident; refute what the data rules out."
)
SYNTH_PROMPT = (
    "You are the Synthesizer. Eliminate refuted hypotheses, elevate the surviving "
    "supported one to a root cause, and propose a remediation. Show the elimination."
)
CRITIC_PROMPT = (
    "You are the Critic. Adversarially verify the root cause: confirm errors began "
    "AFTER the suspected deploy, ensure exactly one hypothesis survived, and require "
    ">=0.80 confidence before approving. Otherwise request a targeted follow-up."
)


def build_workflow(cfg: Config):
    """Construct and return the MAF workflow object for live execution."""
    # Imported lazily; these belong to the [live] extra.
    from agent_framework import ChatAgent, MagenticBuilder, WorkflowBuilder
    from agent_framework.azure import AzureOpenAIChatClient
    from agent_framework.mcp import MCPStdioTool, MCPStreamableHTTPTool

    chat = AzureOpenAIChatClient(
        endpoint=cfg.azure_openai_endpoint,
        api_key=cfg.azure_openai_api_key,
        api_version=cfg.azure_openai_api_version,
        deployment_name=cfg.model_deployment,
    )

    # --- MCP tool servers ------------------------------------------------ #
    azure_mcp = MCPStdioTool(
        name="azure",
        command=cfg.azure_mcp_command,
        args=cfg.azure_mcp_args,
    )
    github_mcp = MCPStreamableHTTPTool(
        name="github",
        url=cfg.github_mcp_url,
        headers={"Authorization": f"Bearer {cfg.github_token}"},
    )

    # --- role agents ----------------------------------------------------- #
    planner = ChatAgent(chat_client=chat, name="Planner", instructions=PLANNER_PROMPT)
    log_agent = ChatAgent(chat_client=chat, name="LogInvestigator",
                          instructions=LOG_PROMPT, tools=[azure_mcp])
    code_agent = ChatAgent(chat_client=chat, name="CodeInvestigator",
                           instructions=CODE_PROMPT, tools=[github_mcp])
    infra_agent = ChatAgent(chat_client=chat, name="InfraInvestigator",
                            instructions=INFRA_PROMPT, tools=[azure_mcp])
    synthesizer = ChatAgent(chat_client=chat, name="Synthesizer", instructions=SYNTH_PROMPT)
    critic = ChatAgent(chat_client=chat, name="Critic", instructions=CRITIC_PROMPT)

    # --- composition ----------------------------------------------------- #
    # Investigators run concurrently (fan-out / fan-in), then a Magentic manager
    # runs the synthesize<->critique loop until the critic approves.
    investigation = (
        WorkflowBuilder(name="investigation")
        .add_fan_out(source=planner, targets=[log_agent, code_agent, infra_agent])
        .add_fan_in(targets=[log_agent, code_agent, infra_agent], destination=synthesizer)
        .build()
    )

    workflow = (
        MagenticBuilder(name="sentinel-rca")
        .participants(investigation=investigation, synthesizer=synthesizer, critic=critic)
        .with_manager(chat_client=chat)
        .with_max_rounds(3)
        .build()
    )
    return workflow


async def run_live(cfg: Config, alert_prompt: str) -> str:
    """Run the live MAF workflow for an incident and return the final report."""
    workflow = build_workflow(cfg)
    result = await workflow.run(alert_prompt)
    return getattr(result, "output", str(result))
