from __future__ import annotations

import ast
import unittest
from pathlib import Path


PACKAGE_DIR = Path(__file__).resolve().parents[1]
ROOT_AGENT_PATH = PACKAGE_DIR / "agent.py"
SPECIALISTS_PATH = PACKAGE_DIR / "agents" / "specialists.py"
PROMPTS_PATH = PACKAGE_DIR / "prompts.py"

EXPECTED_ROOT_CONFIRMED_TOOLS = {
    "save_data_transformations",
    "execute_generated_python_transform",
    "set_ggplot2_case_palette_default",
    "execute_generated_r_plot",
    "execute_generated_r_animation",
}


def _call_name(node: ast.AST) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return ""


def _root_agent_tools(tree: ast.Module) -> list[ast.AST]:
    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        if not any(isinstance(target, ast.Name) and target.id == "root_agent" for target in node.targets):
            continue
        if not isinstance(node.value, ast.Call) or _call_name(node.value.func) != "Agent":
            continue
        for keyword in node.value.keywords:
            if keyword.arg == "tools" and isinstance(keyword.value, ast.List):
                return list(keyword.value.elts)
    raise AssertionError("Could not find root_agent tools list")


class ConfirmationWiringTests(unittest.TestCase):
    def test_confirmation_required_tools_are_direct_root_tools(self) -> None:
        tree = ast.parse(ROOT_AGENT_PATH.read_text(encoding="utf-8"))
        confirmed: set[str] = set()

        for tool_node in _root_agent_tools(tree):
            if not isinstance(tool_node, ast.Call) or _call_name(tool_node.func) != "FunctionTool":
                continue
            self.assertGreaterEqual(len(tool_node.args), 1)
            function_name = _call_name(tool_node.args[0])
            require_confirmation = next(
                (
                    keyword.value.value
                    for keyword in tool_node.keywords
                    if keyword.arg == "require_confirmation"
                    and isinstance(keyword.value, ast.Constant)
                ),
                None,
            )
            if require_confirmation is True:
                confirmed.add(function_name)

        self.assertEqual(confirmed, EXPECTED_ROOT_CONFIRMED_TOOLS)

    def test_nested_specialists_do_not_own_confirmation_tools(self) -> None:
        source = SPECIALISTS_PATH.read_text(encoding="utf-8")
        tree = ast.parse(source)
        function_tool_calls = [
            node
            for node in ast.walk(tree)
            if isinstance(node, ast.Call) and _call_name(node.func) == "FunctionTool"
        ]
        self.assertEqual(function_tool_calls, [])
        self.assertNotIn("require_confirmation=True", source)

        for tool_name in EXPECTED_ROOT_CONFIRMED_TOOLS:
            self.assertNotIn(tool_name, source)

    def test_prompts_distinguish_structured_confirmation_from_chat_approval(self) -> None:
        source = PROMPTS_PATH.read_text(encoding="utf-8")
        self.assertIn("root-level FunctionTool", source)
        self.assertIn('Do not treat a free-text message such as', source)
        self.assertIn('"I approve"', source)
        self.assertIn("do not interpret an empty payload", source)


if __name__ == "__main__":
    unittest.main()
