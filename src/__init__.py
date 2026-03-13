"""
Secure Customer Support Agent - Core Backend Package.

This package contains the agent orchestration (ADK), safety guardrails (Plugins),
and the database tools used by the AI.
"""

from .agent import runner, metrics_plugin

__all__ = ['runner', 'metrics_plugin']