from __future__ import annotations

import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path
from unittest.mock import patch

from PlotWorks.model_config import ModelConfig, missing_credentials, model_backend


class ModelConfigTests(unittest.TestCase):
    def test_legacy_single_model_serves_every_task(self):
        config = ModelConfig.from_env({"MODEL": "one", "PROVIDER": "gemini"})
        for task in (
            "fast",
            "standard",
            "coding",
            "reasoning",
            "python_transformation_code",
        ):
            self.assertEqual(config.candidates(task, "AnyAgent"), ("one",))

    def test_json_single_model_and_list_are_supported(self):
        self.assertEqual(
            ModelConfig.from_env({"MODELS": '["one"]'}).candidates("coding"), ("one",)
        )
        self.assertEqual(
            ModelConfig.from_env({"MODEL": '["one","two"]'}).available, ("one", "two")
        )
        self.assertEqual(ModelConfig.from_env({"MODELS": '"one"'}).available, ("one",))

    def test_profile_task_and_agent_precedence(self):
        config = ModelConfig.from_env(
            {
                "MODELS": '["fast","general","code","deep"]',
                "MODEL": "ignored",
                "MODEL_CODING": '["code","deep"]',
                "MODEL_TASK_OVERRIDES": '{"debug":"deep"}',
                "MODEL_AGENT_OVERRIDES": '{"SpecialAgent":"general"}',
            }
        )
        self.assertEqual(
            config.candidates("write", profile="coding"),
            ("code", "deep", "fast", "general"),
        )
        self.assertEqual(config.candidates("debug", profile="coding")[0], "deep")
        self.assertEqual(
            config.candidates("debug", "SpecialAgent", "coding")[0], "general"
        )
        self.assertEqual(config.candidates("unassigned"), config.available)

    def test_malformed_or_unregistered_models_fail_early(self):
        cases = [
            {"MODELS": "[]"},
            {"MODELS": '["a",2]'},
            {"MODELS": '["a"', "MODEL": "old"},
            {"MODEL": "a", "MODEL_CODING": "missing"},
            {"MODEL": "a", "MODEL_AGENT_OVERRIDES": "[]"},
            {"MODEL": "a", "MODEL_MAX_RETRIES": "5"},
            {"PROVIDER": "unknown"},
            {"MODEL": "a", "MODEL_TASK_OVERRIDES": '{"code":[]}'},
        ]
        for env in cases:
            with self.subTest(env=env), self.assertRaises(ValueError):
                ModelConfig.from_env(env)

    def test_provider_resolution_supports_mixed_backends_and_legacy_litellm(self):
        self.assertEqual(
            model_backend("gemini/my-model", "litellm"), ("gemini", "my-model")
        )
        self.assertEqual(
            model_backend("anthropic/my-model"), ("litellm", "anthropic/my-model")
        )
        self.assertEqual(model_backend("bare", "litellm"), ("litellm", "bare"))
        self.assertEqual(
            model_backend("litellm/gemini/my-model"), ("litellm", "gemini/my-model")
        )

    def test_credentials_are_checked_without_exposing_values(self):
        self.assertIn("GOOGLE_API_KEY", missing_credentials("gemini/a", "gemini", {}))
        self.assertEqual(
            missing_credentials("gemini/a", "gemini", {"GEMINI_API_KEY": "secret"}), ""
        )
        self.assertEqual(
            missing_credentials("anthropic/a", "gemini", {}), "ANTHROPIC_API_KEY"
        )
        self.assertEqual(
            missing_credentials(
                "gemini/a", "gemini", {"GOOGLE_GENAI_USE_VERTEXAI": "true"}
            ),
            "",
        )


try:
    from google.adk.models.llm_request import LlmRequest
    from google.adk.models.llm_response import LlmResponse
    from google.genai import types
    from PlotWorks.routing_model import AvailabilityError, RoutedModel

    ADK = True
except ModuleNotFoundError:
    ADK = False


@unittest.skipUnless(ADK, "google-adk is required for adapter tests")
class RoutedModelTests(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        from PlotWorks.config import settings

        self.enterContext(
            patch(
                "PlotWorks.routing_model.settings",
                replace(settings, output_dir=Path(self.temporary.name)),
            )
        )
        self.config = ModelConfig.from_env(
            {
                "MODELS": '["gemini/first","openai/second"]',
                "MODEL_MAX_RETRIES": "1",
                "MODEL_RETRY_DELAY_SECONDS": "0",
            }
        )
        self.model = RoutedModel(
            model="first",
            candidates=self.config.available,
            routing=self.config,
            task="code",
            profile="coding",
            agent_name="Developer",
        )
        self.request = LlmRequest(
            contents=[
                types.Content(role="user", parts=[types.Part(text="private input")])
            ]
        )

    def delegate(self, actions, name):
        class Delegate:
            model = name
            calls = []

            async def generate_content_async(inner, request, stream=False):
                inner.calls.append(request)
                action = actions.pop(0)
                if isinstance(action, Exception):
                    request.contents.append(
                        types.Content(role="user", parts=[types.Part(text="mutation")])
                    )
                    raise action
                for response in action:
                    if isinstance(response, Exception):
                        raise response
                    yield response

        return Delegate()

    async def collect(self):
        return [
            response
            async for response in self.model.generate_content_async(self.request)
        ]

    def test_provider_specific_features_filter_incompatible_candidates(self):
        from PlotWorks.llm_factory import build_model

        with patch.dict(
            "os.environ",
            {
                "MODELS": '["anthropic/code","gemini/search"]',
                "MODEL_CHECK_CREDENTIALS": "false",
            },
            clear=True,
        ):
            model = build_model(
                task="method_research", profile="standard", required_backend="gemini"
            )
        self.assertEqual(model.candidates, ("gemini/search",))

    def test_provider_specific_features_fail_clearly_without_a_compatible_model(self):
        from PlotWorks.llm_factory import build_model

        with patch.dict(
            "os.environ",
            {"MODEL": "anthropic/code", "MODEL_CHECK_CREDENTIALS": "false"},
            clear=True,
        ):
            with self.assertRaisesRegex(ValueError, "requires a gemini model"):
                build_model(task="method_research", required_backend="gemini")

    async def test_availability_retry_then_fallback_and_usage_logging(self):
        first = self.delegate([AvailabilityError(429), TimeoutError()], "first")
        second = self.delegate(
            [
                [
                    LlmResponse(
                        content=types.Content(
                            role="model", parts=[types.Part(text="ok")]
                        ),
                        usage_metadata=types.GenerateContentResponseUsageMetadata(
                            prompt_token_count=10,
                            candidates_token_count=5,
                            total_token_count=15,
                        ),
                    )
                ]
            ],
            "openai/second",
        )
        self.model._delegates.update({"gemini/first": first, "openai/second": second})
        result = await self.collect()
        self.assertEqual(len(first.calls), 2)
        self.assertEqual(len(second.calls), 1)
        self.assertEqual(len(self.request.contents), 1)
        self.assertEqual(len(second.calls[0].contents), 1)
        self.assertEqual(second.calls[0].model, "openai/second")
        self.assertTrue(result[0].custom_metadata["plotworks_routing"]["fallback"])
        text = (Path(self.temporary.name) / "logs/model_calls.jsonl").read_text()
        self.assertNotIn("private input", text)
        records = [json.loads(line) for line in text.splitlines()]
        self.assertEqual(len(records), 3)
        self.assertEqual(records[-1]["usage"]["total_token_count"], 15)

    async def test_no_fallback_after_any_response_or_tool_call(self):
        response = LlmResponse(
            content=types.Content(
                role="model",
                parts=[
                    types.Part(function_call=types.FunctionCall(name="save", args={}))
                ],
            ),
            partial=True,
        )
        first = self.delegate([[response, TimeoutError()]], "first")
        second = self.delegate([], "openai/second")
        self.model._delegates.update({"gemini/first": first, "openai/second": second})
        with self.assertRaises(TimeoutError):
            await self.collect()
        self.assertEqual(len(first.calls), 1)
        self.assertEqual(second.calls, [])

    async def test_invalid_requests_do_not_trigger_fallback(self):
        first = self.delegate([ValueError("invalid request")], "first")
        self.model._delegates["gemini/first"] = first
        with self.assertRaises(ValueError):
            await self.collect()
        self.assertEqual(len(first.calls), 1)

    async def test_retries_are_bounded_when_all_models_fail(self):
        first = self.delegate([TimeoutError(), TimeoutError()], "first")
        second = self.delegate([TimeoutError(), TimeoutError()], "openai/second")
        self.model._delegates.update({"gemini/first": first, "openai/second": second})
        with self.assertRaises(TimeoutError):
            await self.collect()
        self.assertEqual((len(first.calls), len(second.calls)), (2, 2))

    async def test_response_availability_codes_can_fall_back_but_safety_blocks_do_not(
        self,
    ):
        self.model.routing = replace(self.config, retries=0)
        first = self.delegate([[LlmResponse(error_code="503")]], "first")
        second = self.delegate(
            [
                [
                    LlmResponse(
                        content=types.Content(
                            role="model", parts=[types.Part(text="ok")]
                        )
                    )
                ]
            ],
            "openai/second",
        )
        self.model._delegates.update({"gemini/first": first, "openai/second": second})
        self.assertEqual(len(await self.collect()), 1)
        self.model._delegates["gemini/first"] = self.delegate(
            [[LlmResponse(error_code="SAFETY")]], "first"
        )
        result = await self.collect()
        self.assertEqual(result[0].error_code, "SAFETY")
        self.assertEqual(len(second.calls), 1)
