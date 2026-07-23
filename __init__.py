"""Data Analysis Agency package.

ADK discovers root_agent from agent.py when the package is run as an ADK app.
The guarded import keeps local utility modules importable in lightweight contexts
where google-adk has not been installed yet.
"""

try:  # pragma: no cover - exercised by ADK runtime
    from . import agent  # noqa: F401
except ModuleNotFoundError as exc:  # allows importing tools before ADK is installed
    if exc.name != "google.adk":
        raise
