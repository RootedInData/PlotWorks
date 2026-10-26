from __future__ import annotations

from .config import settings  # noqa: F401  # load the package .env before resolving model preferences
from .model_config import ModelConfig, missing_credentials, model_backend


def model_configuration(check_credentials: bool = False) -> dict:
    """Return identifiers and routing only; never include credential values."""
    config = ModelConfig.from_env()
    result = {
        "models": list(config.available),
        "profiles": {p: list(config.candidates(p)) for p in config.profiles},
        "task_overrides": config.task_overrides,
        "agent_overrides": config.agent_overrides,
        "single_model": len(config.available) == 1,
    }
    if check_credentials:
        result["missing_credentials"] = {
            name: key
            for name in config.available
            if (key := missing_credentials(name, config.provider))
        }
    return result


def build_model(
    task: str = "standard",
    agent_name: str = "",
    profile: str = "",
    required_backend: str = "",
):
    """Resolve a replaceable task profile through the shared ADK adapter.

    Fallback happens only inside a model request, before any response is emitted;
    it cannot replay agent tools or completed file writes.
    """
    config = ModelConfig.from_env()
    candidates = config.candidates(task, agent_name, profile)
    if required_backend:
        candidates = tuple(
            name
            for name in candidates
            if model_backend(name, config.provider)[0] == required_backend
        )
        if not candidates:
            raise ValueError(
                f"Task {task} requires a {required_backend} model; configure a compatible candidate or disable that provider-specific feature"
            )
    if config.check_credentials:
        missing = {
            name: key
            for name in candidates
            if (key := missing_credentials(name, config.provider))
        }
        if missing:
            details = "; ".join(f"{name}: {key}" for name, key in missing.items())
            raise ValueError(
                f"Missing model credentials ({details}). Configure .env before starting PlotWorks."
            )
    from .routing_model import RoutedModel

    return RoutedModel(
        model=model_backend(candidates[0], config.provider)[1],
        candidates=candidates,
        routing=config,
        task=task,
        agent_name=agent_name,
        profile=profile or task,
    )


if __name__ == "__main__":
    import json

    print(json.dumps(model_configuration(check_credentials=True), indent=2))
