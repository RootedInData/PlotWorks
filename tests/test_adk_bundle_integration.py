"""Offline ADK 2.5.0 execution, including nested state and confirmation resume."""

from __future__ import annotations

import json
import unittest
from unittest.mock import patch

from PlotWorks.tests.bundle_test_support import BundleTestCase

try:
    from google.adk import Agent
    from google.adk.models.base_llm import BaseLlm
    from google.adk.models.llm_response import LlmResponse
    from google.adk.runners import InMemoryRunner
    from google.adk.tools.agent_tool import AgentTool
    from google.adk.tools.function_tool import FunctionTool
    from google.genai import types
    from pydantic import PrivateAttr

    ADK = True
except ModuleNotFoundError:
    ADK = False

from PlotWorks.tools import (
    preview_bundle_transformations,
    register_dataset_bundle,
    save_bundle_transformation,
)
from PlotWorks.tools.dataset_bundle_tools import BUNDLES_KEY, PROPOSALS_KEY


def last_response(request, name):
    for content in reversed(request.contents):
        for part in content.parts or []:
            response = part.function_response
            if response and response.name == name:
                value = response.response
                if isinstance(value, dict) and "result" in value:
                    value = value["result"]
                return json.loads(value) if isinstance(value, str) else value
    raise AssertionError(f"Missing tool response {name}")


if ADK:

    class WorkflowModel(BaseLlm):
        role: str
        datasets_json: str = ""
        operations_json: str = ""
        _step: int = PrivateAttr(default=0)

        async def generate_content_async(self, request, stream=False):
            step = self._step
            self._step += 1
            if self.role == "intake":
                if step == 0:
                    name, arguments = (
                        "register_dataset_bundle",
                        {"datasets_json": self.datasets_json},
                    )
                else:
                    result = last_response(request, "register_dataset_bundle")
                    if result["status"] != "success":
                        raise AssertionError(result)
                    yield LlmResponse(
                        content=types.Content(
                            role="model",
                            parts=[
                                types.Part(
                                    text=json.dumps(
                                        {
                                            "status": "success",
                                            "bundle_id": result["bundle_id"],
                                        }
                                    )
                                )
                            ],
                        )
                    )
                    return
            elif self.role == "prepare":
                if step == 0:
                    name, arguments = (
                        "preview_bundle_transformations",
                        {
                            "operations_json": self.operations_json,
                            "output_names_json": '{"plot_ready":"adk/joined.csv"}',
                        },
                    )
                else:
                    result = last_response(request, "preview_bundle_transformations")
                    if result["status"] != "success":
                        raise AssertionError(result)
                    yield LlmResponse(
                        content=types.Content(
                            role="model",
                            parts=[
                                types.Part(
                                    text=json.dumps(
                                        {
                                            "status": "success",
                                            "proposal": result["proposal"],
                                        }
                                    )
                                )
                            ],
                        )
                    )
                    return
            else:
                if step == 0:
                    name, arguments = (
                        "IntakeAgent",
                        {"request": "Register the selected input files"},
                    )
                elif step == 1:
                    name, arguments = (
                        "PreparationAgent",
                        {"request": "Preview the join using the active bundle"},
                    )
                elif step == 2:
                    result = last_response(request, "PreparationAgent")
                    name, arguments = (
                        "save_bundle_transformation",
                        {"proposal_json": json.dumps(result["proposal"])},
                    )
                else:
                    yield LlmResponse(
                        content=types.Content(
                            role="model", parts=[types.Part(text="Workflow complete")]
                        )
                    )
                    return
            yield LlmResponse(
                content=types.Content(
                    role="model",
                    parts=[
                        types.Part(
                            function_call=types.FunctionCall(name=name, args=arguments)
                        )
                    ],
                )
            )


@unittest.skipUnless(ADK, "Install google-adk==2.5.0 for offline integration tests")
class AdkBundleIntegrationTests(BundleTestCase, unittest.IsolatedAsyncioTestCase):
    async def begin(self):
        self.a = self.source("a.csv", "id,value\n1,10\n2,20\n")
        self.b = self.source("b.csv", "id,group\n1,A\n2,B\n")
        intake = Agent(
            name="IntakeAgent",
            model=WorkflowModel(
                model="fake",
                role="intake",
                datasets_json='{"traits":"a.csv","metadata":"b.csv"}',
            ),
            tools=[register_dataset_bundle],
        )
        preparation = Agent(
            name="PreparationAgent",
            model=WorkflowModel(
                model="fake",
                role="prepare",
                operations_json='[{"operation":"join","left":"traits","right":"metadata","on":"id","how":"left","validate":"many_to_one","output":"plot_ready"}]',
            ),
            tools=[preview_bundle_transformations],
        )
        root = Agent(
            name="Supervisor",
            model=WorkflowModel(model="fake", role="root"),
            tools=[
                AgentTool(intake),
                AgentTool(preparation),
                FunctionTool(save_bundle_transformation, require_confirmation=True),
            ],
        )
        self.runner = InMemoryRunner(agent=root, app_name="plotworks_offline_test")
        self.addAsyncCleanup(self.runner.close)
        self.session = await self.runner.session_service.create_session(
            app_name="plotworks_offline_test", user_id="test"
        )
        events = [
            event
            async for event in self.runner.run_async(
                user_id="test",
                session_id=self.session.id,
                new_message=types.Content(
                    role="user", parts=[types.Part(text="Join these datasets")]
                ),
            )
        ]
        calls = [
            call
            for event in events
            for call in event.get_function_calls()
            if call.name == "adk_request_confirmation"
        ]
        self.assertEqual(len(calls), 1)
        self.assertFalse(list(self.settings.transformed_data_output_dir.rglob("*.csv")))
        saved_session = await self.runner.session_service.get_session(
            app_name="plotworks_offline_test",
            user_id="test",
            session_id=self.session.id,
        )
        self.assertTrue(saved_session.state[BUNDLES_KEY])
        self.assertTrue(saved_session.state[PROPOSALS_KEY])
        json.dumps(saved_session.state, allow_nan=False)
        return calls[0]

    async def resume(self, call, confirmed):
        response = types.FunctionResponse(
            id=call.id,
            name="adk_request_confirmation",
            response={"confirmed": confirmed},
        )
        return [
            event
            async for event in self.runner.run_async(
                user_id="test",
                session_id=self.session.id,
                new_message=types.Content(
                    role="user", parts=[types.Part(function_response=response)]
                ),
            )
        ]

    async def test_nested_handoff_confirmation_and_resume_save_the_exact_preview(self):
        call = await self.begin()
        events = await self.resume(call, True)
        results = [
            r.response
            for event in events
            for r in event.get_function_responses()
            if r.name == "save_bundle_transformation"
        ]
        self.assertTrue(results)
        self.assertEqual(results[-1]["status"], "success", results)
        self.assertEqual(
            len(list(self.settings.transformed_data_output_dir.rglob("*.csv"))), 1
        )

    async def test_rejected_confirmation_does_not_publish(self):
        call = await self.begin()
        await self.resume(call, False)
        self.assertFalse(list(self.settings.transformed_data_output_dir.rglob("*.csv")))

    async def test_source_change_while_confirmation_is_pending_requires_a_new_preview(
        self,
    ):
        call = await self.begin()
        self.b.write_text("id,group\n1,changed\n", encoding="utf-8")
        events = await self.resume(call, True)
        results = [
            r.response
            for event in events
            for r in event.get_function_responses()
            if r.name == "save_bundle_transformation"
        ]
        self.assertEqual(results[-1]["status"], "error", results)
        self.assertIn("changed", results[-1]["message"])
        self.assertFalse(list(self.settings.transformed_data_output_dir.rglob("*.csv")))

    def test_framework_schemas_hide_tool_context_and_root_agents_use_profiles(self):
        for function in (
            register_dataset_bundle,
            preview_bundle_transformations,
            save_bundle_transformation,
        ):
            declaration = (
                FunctionTool(function)._get_declaration().model_dump(exclude_none=True)
            )
            schema = (
                declaration.get("parameters_json_schema") or declaration["parameters"]
            )
            self.assertNotIn("tool_context", schema["properties"])
        with patch.dict("os.environ", {"MODEL_CHECK_CREDENTIALS": "false"}):
            from PlotWorks.agent import root_agent
        self.assertEqual(root_agent.model.profile, "standard")
        agents = {
            tool.agent.name: tool.agent
            for tool in root_agent.tools
            if isinstance(tool, AgentTool)
        }
        self.assertEqual(agents["DataIntakeAgent"].model.profile, "fast")
        self.assertEqual(
            agents["PythonTransformDeveloperAgent"].model.profile, "coding"
        )
        self.assertEqual(agents["ReasoningAgent"].model.profile, "reasoning")
