"""PlotWorks utilities can be imported without constructing model clients.

ADK discovers the agent submodule normally. Lazy access also preserves
``from PlotWorks import agent`` without requiring API keys for local data tools.
"""

from importlib import import_module


def __getattr__(name: str):
    if name == "agent":
        return import_module(".agent", __name__)
    raise AttributeError(name)
