"""Reasoning-model client.

LIVE mode talks to a Microsoft Foundry / Azure OpenAI reasoning deployment
(GPT-5.2 or MAI-Thinking-1). MOCK mode never instantiates this — the agents'
deterministic analytical core runs instead and the LLM layer is skipped, so the
demo needs no keys and no network.

The point of separating this out: in LIVE mode the LLM generalizes Sentinel
beyond the canned scenario (free-form hypothesis generation + narrative), while
the *evidence scoring and hypothesis elimination remain deterministic Python*
so the conclusion is always grounded in real telemetry, not vibes.
"""

from __future__ import annotations

import json
from typing import Any


class FoundryChatClient:
    """Thin wrapper over the Azure OpenAI / Foundry chat completions API."""

    def __init__(self, cfg: Any) -> None:
        # Imported lazily so mock mode has zero third-party dependencies.
        from openai import AzureOpenAI

        self._client = AzureOpenAI(
            azure_endpoint=cfg.azure_openai_endpoint,
            api_key=cfg.azure_openai_api_key,
            api_version=cfg.azure_openai_api_version,
        )
        self._model = cfg.model_deployment

    def complete(self, system: str, user: str, *, json_mode: bool = False) -> str:
        kwargs: dict[str, Any] = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = self._client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""

    def complete_json(self, system: str, user: str) -> dict:
        raw = self.complete(system, user, json_mode=True)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {}
