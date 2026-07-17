from __future__ import annotations

from google.adk import Agent
from google.adk.tools.agent_tool import AgentTool

from .agent_cards import AGENT_CARDS
from .agents import (
    build_code_planning_agent,
    build_data_intake_agent,
    build_eda_agent,
    build_method_research_agent,
    build_report_agent,
    build_visualization_agent,
)
from .llm_factory import build_model
from .prompts import SUPERVISOR_PROMPT

# Specialist agents. The supervisor uses these as callable tools.
data_intake_agent = build_data_intake_agent()
eda_agent = build_eda_agent()
visualization_agent = build_visualization_agent()
code_planning_agent = build_code_planning_agent()
report_agent = build_report_agent()
method_research_agent = build_method_research_agent()

root_agent = Agent(
    name="DataAnalysisAgencySupervisor",
    model=build_model(),
    description=(
        "Supervisor for the Data Analysis Agency. Dynamically plans the analysis and "
        "recruits specialist data agents based on their description cards."
    ),
    instruction=SUPERVISOR_PROMPT + "\n\n" + AGENT_CARDS,
    tools=[
        AgentTool(agent=data_intake_agent),
        AgentTool(agent=eda_agent),
        AgentTool(agent=visualization_agent),
        AgentTool(agent=code_planning_agent),
        AgentTool(agent=report_agent),
        AgentTool(agent=method_research_agent),
    ],
)
