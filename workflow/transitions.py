"""Workflow state transition rule engine interface."""

from abc import ABC, abstractmethod

from workflow.states import WorkflowState


class BaseWorkflowTransitionEngine(ABC):
    """Abstract interface governing allowed task state transitions."""

    @abstractmethod
    def can_transition(self, current_state: WorkflowState, target_state: WorkflowState) -> bool:
        """Check if transitioning from current_state to target_state is allowed."""
        pass
