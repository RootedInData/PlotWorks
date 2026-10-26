"""ADK model adapter with bounded availability fallback and prompt-free telemetry."""

from __future__ import annotations

import asyncio
import json
import logging
import time
import uuid
from datetime import datetime, timezone
from typing import Any

from google.adk.models.base_llm import BaseLlm
from pydantic import Field, PrivateAttr

from .config import settings
from .model_config import ModelConfig, model_backend

logger = logging.getLogger(__name__)
_TRANSIENT_CODES = {408, 429, 500, 502, 503, 504}
_TRANSIENT_NAMES = {
    "RESOURCE_EXHAUSTED",
    "UNAVAILABLE",
    "DEADLINE_EXCEEDED",
    "INTERNAL",
    "OVERLOADED",
}


class AvailabilityError(RuntimeError):
    def __init__(self, code):
        self.status_code = code
        super().__init__(f"Provider availability failure: {code}")


def _transient(exc: Exception) -> bool:
    if isinstance(exc, (TimeoutError, ConnectionError)):
        return True
    code = getattr(exc, "status_code", getattr(exc, "code", None))
    if callable(code):
        code = code()
    try:
        return int(code) in _TRANSIENT_CODES
    except (TypeError, ValueError):
        return str(code).upper() in _TRANSIENT_NAMES or type(exc).__name__ in {
            "APITimeoutError",
            "APIConnectionError",
            "ConnectError",
            "ReadTimeout",
            "ConnectTimeout",
        }


def _usage(response) -> dict[str, int]:
    metadata = getattr(response, "usage_metadata", None)
    return {
        key: int(value)
        for key in (
            "prompt_token_count",
            "candidates_token_count",
            "total_token_count",
            "cached_content_token_count",
            "thoughts_token_count",
        )
        if (value := getattr(metadata, key, None)) is not None
    }


class RoutedModel(BaseLlm):
    candidates: tuple[str, ...]
    routing: ModelConfig = Field(exclude=True)
    task: str = "standard"
    profile: str = "standard"
    agent_name: str = ""
    _delegates: dict[str, Any] = PrivateAttr(default_factory=dict)

    def _delegate(self, identifier: str):
        if identifier not in self._delegates:
            backend, model = model_backend(identifier, self.routing.provider)
            if backend == "gemini":
                from google.adk.models.google_llm import Gemini
                from google.genai import types

                self._delegates[identifier] = Gemini(
                    model=model, retry_options=types.HttpRetryOptions(attempts=1)
                )
            else:
                from google.adk.models.lite_llm import LiteLlm

                # Disable hidden LiteLLM retries; this adapter owns the retry bound.
                self._delegates[identifier] = LiteLlm(model=model, num_retries=0)
        return self._delegates[identifier]

    def _record(self, record: dict) -> None:
        if not self.routing.log_calls:
            return
        try:
            folder = settings.output_dir / "logs"
            folder.mkdir(parents=True, exist_ok=True)
            with (folder / "model_calls.jsonl").open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, separators=(",", ":")) + "\n")
        except OSError:
            logger.warning("Unable to write model-call telemetry")

    async def generate_content_async(self, llm_request, stream: bool = False):
        call_id = uuid.uuid4().hex
        previous_failure = None
        attempt_number = 0
        for candidate_index, candidate in enumerate(self.candidates):
            for retry in range(self.routing.retries + 1):
                attempt_number += 1
                start = time.monotonic()
                emitted = False
                usage = {}
                provider_error = False
                record = {
                    "call_id": call_id,
                    "timestamp": datetime.now(timezone.utc).isoformat(),
                    "agent": self.agent_name,
                    "task": self.task,
                    "profile": self.profile,
                    "model": candidate,
                    "attempt": attempt_number,
                    "retry": retry,
                    "fallback": candidate_index > 0,
                    "fallback_reason": previous_failure,
                }
                try:
                    delegate = self._delegate(candidate)
                    # Provider preprocessing may mutate a request. Each attempt starts
                    # from the untouched turn; framework tool objects are retained.
                    request = llm_request.model_copy(
                        update={
                            "model": delegate.model,
                            "contents": [
                                c.model_copy(deep=True) for c in llm_request.contents
                            ],
                            "config": llm_request.config.model_copy(deep=True),
                        }
                    )
                    # Prevent provider SDK retries from multiplying this adapter's
                    # configured retry bound. Preserve unrelated HTTP settings.
                    from google.genai import types

                    backend, _ = model_backend(candidate, self.routing.provider)
                    if backend == "gemini":
                        options = request.config.http_options or types.HttpOptions()
                        request.config.http_options = options.model_copy(
                            update={"retry_options": types.HttpRetryOptions(attempts=1)}
                        )
                    elif request.config.http_options is not None:
                        request.config.http_options = (
                            request.config.http_options.model_copy(
                                update={"retry_options": None}
                            )
                        )
                    if candidate_index:
                        request.cache_config = None
                        request.cache_metadata = None
                        request.previous_interaction_id = None
                    async for response in delegate.generate_content_async(
                        request, stream=stream
                    ):
                        code = response.error_code
                        provider_error = provider_error or bool(code)
                        if code and not emitted:
                            error = AvailabilityError(code)
                            if _transient(error):
                                raise error
                        emitted = True
                        usage.update(_usage(response))
                        response.custom_metadata = {
                            **(response.custom_metadata or {}),
                            "plotworks_routing": {
                                "model": candidate,
                                "profile": self.profile,
                                "task": self.task,
                                "agent": self.agent_name,
                                "call_id": call_id,
                                "attempt": attempt_number,
                                "fallback": candidate_index > 0,
                            },
                        }
                        yield response
                    if not emitted:
                        raise RuntimeError("Provider returned an empty response stream")
                    self._record(
                        {
                            **record,
                            "status": "provider_error" if provider_error else "success",
                            "latency_ms": round((time.monotonic() - start) * 1000),
                            "usage": usage,
                        }
                    )
                    return
                except Exception as exc:
                    retryable = _transient(exc) and not emitted
                    previous_failure = type(exc).__name__
                    self._record(
                        {
                            **record,
                            "status": "error",
                            "latency_ms": round((time.monotonic() - start) * 1000),
                            "error_type": type(exc).__name__,
                            "retryable": retryable,
                            "usage": usage,
                        }
                    )
                    if not retryable:
                        raise
                    last = (
                        candidate_index == len(self.candidates) - 1
                        and retry == self.routing.retries
                    )
                    if last:
                        raise
                    if retry < self.routing.retries:
                        await asyncio.sleep(
                            min(30, self.routing.retry_delay_seconds * (2**retry))
                        )
        raise RuntimeError(
            "No model candidates were available"
        )  # unreachable after validated config
