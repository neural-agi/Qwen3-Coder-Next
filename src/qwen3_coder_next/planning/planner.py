"""Planner abstraction for the foundation layer."""

from abc import ABC, abstractmethod

from qwen3_coder_next.planning.contracts import PlanRequest, PlanResult


class Planner(ABC):
    """Abstract planner interface."""

    @abstractmethod
    def plan(self, request: PlanRequest) -> PlanResult:
        """Create a plan for the supplied request."""

