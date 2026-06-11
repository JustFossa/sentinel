"""Runtime configuration. Reads environment, decides mock vs live."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


def _load_dotenv() -> None:
    """Tiny .env loader so we don't hard-depend on python-dotenv for the demo."""
    env_path = Path.cwd() / ".env"
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip())


@dataclass
class Config:
    mode: str = "mock"  # "mock" | "live"

    # Foundry / Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_api_version: str = "2025-04-01-preview"
    model_deployment: str = "gpt-5.2"

    # Azure MCP
    azure_mcp_command: str = "npx"
    azure_mcp_args: list[str] = field(default_factory=lambda: ["-y", "@azure/mcp@latest", "server", "start"])
    azure_subscription_id: str = ""

    # GitHub MCP
    github_mcp_url: str = "https://api.githubcopilot.com/mcp/"
    github_token: str = ""
    github_repo: str = "your-org/your-service"

    # Observability
    otlp_endpoint: str = ""

    @property
    def is_live(self) -> bool:
        return self.mode == "live"

    @classmethod
    def load(cls, mode_override: str | None = None) -> "Config":
        _load_dotenv()
        args = os.getenv("AZURE_MCP_ARGS", "")
        return cls(
            mode=(mode_override or os.getenv("SENTINEL_MODE", "mock")).lower(),
            azure_openai_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT", ""),
            azure_openai_api_key=os.getenv("AZURE_OPENAI_API_KEY", ""),
            azure_openai_api_version=os.getenv("AZURE_OPENAI_API_VERSION", "2025-04-01-preview"),
            model_deployment=os.getenv("SENTINEL_MODEL_DEPLOYMENT", "gpt-5.2"),
            azure_mcp_command=os.getenv("AZURE_MCP_COMMAND", "npx"),
            azure_mcp_args=[a for a in args.split(",") if a] or ["-y", "@azure/mcp@latest", "server", "start"],
            azure_subscription_id=os.getenv("AZURE_SUBSCRIPTION_ID", ""),
            github_mcp_url=os.getenv("GITHUB_MCP_URL", "https://api.githubcopilot.com/mcp/"),
            github_token=os.getenv("GITHUB_PERSONAL_ACCESS_TOKEN", ""),
            github_repo=os.getenv("GITHUB_REPO", "your-org/your-service"),
            otlp_endpoint=os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", ""),
        )
