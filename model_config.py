"""Provider-independent, environment-driven model preferences.

No provider client is constructed here. This module is safe to use in diagnostics
and unit tests without credentials or google-adk installed.
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Mapping

PROFILES = ("fast", "standard", "coding", "reasoning")


def _models(value: str, label: str) -> tuple[str, ...]:
    raw = str(value).strip()
    if not raw:
        return ()
    if raw.startswith("[") or raw.startswith('"'):
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as exc:
            raise ValueError(
                f"{label} must be a model ID or JSON array of model IDs"
            ) from exc
        parsed = [parsed] if isinstance(parsed, str) else parsed
    else:
        parsed = raw.split(",")
    if not isinstance(parsed, list) or not all(
        isinstance(x, str) and x.strip() for x in parsed
    ):
        raise ValueError(f"{label} must contain nonempty model IDs")
    return tuple(dict.fromkeys(x.strip() for x in parsed))


def _overrides(raw: str, label: str) -> dict[str, tuple[str, ...]]:
    if not raw.strip():
        return {}
    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise ValueError(f"{label} must be a JSON object") from exc
    if not isinstance(parsed, dict):
        raise ValueError(f"{label} must be a JSON object")
    result = {}
    for key, value in parsed.items():
        if (
            not isinstance(key, str)
            or not key.strip()
            or not isinstance(value, (str, list))
        ):
            raise ValueError(f"Invalid entry in {label}")
        result[key] = _models(json.dumps(value), f"{label}.{key}")
        if not result[key]:
            raise ValueError(f"{label}.{key} cannot be empty")
    return result


@dataclass(frozen=True)
class ModelConfig:
    available: tuple[str, ...]
    profiles: dict[str, tuple[str, ...]]
    task_overrides: dict[str, tuple[str, ...]]
    agent_overrides: dict[str, tuple[str, ...]]
    provider: str = "gemini"
    retries: int = 1
    retry_delay_seconds: float = 1.0
    check_credentials: bool = True
    log_calls: bool = True

    @classmethod
    def from_env(cls, environ: Mapping[str, str] | None = None) -> "ModelConfig":
        env = os.environ if environ is None else environ
        provider = env.get("PROVIDER", "gemini").strip().lower()
        if provider not in {"gemini", "litellm"}:
            raise ValueError("PROVIDER must be gemini or litellm")
        available = (
            _models(env["MODELS"], "MODELS")
            if env.get("MODELS", "").strip()
            else _models(env.get("MODEL", "gemini-flash-latest"), "MODEL")
        )
        if not available:
            raise ValueError("Configure at least one model using MODEL or MODELS")
        profiles = {
            p: _models(env.get(f"MODEL_{p.upper()}", ""), f"MODEL_{p.upper()}")
            for p in PROFILES
        }
        tasks = _overrides(env.get("MODEL_TASK_OVERRIDES", ""), "MODEL_TASK_OVERRIDES")
        agents = _overrides(
            env.get("MODEL_AGENT_OVERRIDES", ""), "MODEL_AGENT_OVERRIDES"
        )
        for label, preferences in (*profiles.items(), *tasks.items(), *agents.items()):
            unknown = set(preferences) - set(available)
            if unknown:
                raise ValueError(
                    f"{label} references unregistered models: {sorted(unknown)}; add them to MODELS"
                )
        retries = int(env.get("MODEL_MAX_RETRIES", "1"))
        delay = float(env.get("MODEL_RETRY_DELAY_SECONDS", "1"))
        if not 0 <= retries <= 3 or not 0 <= delay <= 30:
            raise ValueError(
                "MODEL_MAX_RETRIES must be 0..3 and MODEL_RETRY_DELAY_SECONDS 0..30"
            )
        truthy = {"1", "true", "yes", "y"}
        return cls(
            available,
            profiles,
            tasks,
            agents,
            provider,
            retries,
            delay,
            env.get("MODEL_CHECK_CREDENTIALS", "true").lower() in truthy,
            env.get("MODEL_LOG_CALLS", "true").lower() in truthy,
        )

    def candidates(
        self, task: str = "standard", agent_name: str = "", profile: str = ""
    ) -> tuple[str, ...]:
        if len(self.available) == 1:
            return self.available
        preferred = (
            self.agent_overrides.get(agent_name)
            or self.task_overrides.get(task)
            or self.profiles.get(profile or task)
            or ()
        )
        return tuple(dict.fromkeys((*preferred, *self.available)))


def model_backend(identifier: str, provider: str = "gemini") -> tuple[str, str]:
    """Explicit prefixes take precedence; bare IDs retain legacy PROVIDER behavior."""
    if identifier.startswith("litellm/"):
        return "litellm", identifier.removeprefix("litellm/")
    if identifier.startswith("gemini/"):
        return "gemini", identifier.removeprefix("gemini/")
    if "/" in identifier:
        return "litellm", identifier
    return provider, identifier


def missing_credentials(
    identifier: str, provider: str, environ: Mapping[str, str] | None = None
) -> str:
    env = os.environ if environ is None else environ
    backend, name = model_backend(identifier, provider)
    if backend == "gemini" or name.startswith("gemini/"):
        if env.get("GOOGLE_GENAI_USE_VERTEXAI", "").lower() in {"true", "1"}:
            return ""  # ADC is resolved by the provider; do not probe credential files.
        return (
            ""
            if env.get("GOOGLE_API_KEY") or env.get("GEMINI_API_KEY")
            else "GOOGLE_API_KEY or GEMINI_API_KEY"
        )
    prefix = name.split("/", 1)[0]
    key = {
        "openai": "OPENAI_API_KEY",
        "anthropic": "ANTHROPIC_API_KEY",
        "groq": "GROQ_API_KEY",
        "mistral": "MISTRAL_API_KEY",
        "azure": "AZURE_API_KEY",
    }.get(prefix)
    return key if key and not env.get(key) else ""
