"""
Reflection Subsystem

Transforms AgentOS into a learning system by analyzing completed executions
and providing structured, deterministic feedback.

This subsystem is explicitly read-only and must never modify execution state.
"""

from supervisor.reflection.engine import ReflectionEngine

__all__ = ["ReflectionEngine"]
