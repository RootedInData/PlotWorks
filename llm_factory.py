from __future__ import annotations

from .config import settings


def build_model():
    """Return the model object/string to pass into ADK LlmAgent/Agent.

    Gemini can be passed as a string directly. Other providers are routed through
    LiteLLM, which lets you switch providers without changing the agent code.
    """

    if settings.provider == "gemini":
        return settings.model

    if settings.provider == "litellm":
        from google.adk.models.lite_llm import LiteLlm

        return LiteLlm(model=settings.model)

    raise ValueError(
        "Unsupported PROVIDER. Use PROVIDER=gemini or PROVIDER=litellm. "
        f"Current value: {settings.provider!r}"
    )
