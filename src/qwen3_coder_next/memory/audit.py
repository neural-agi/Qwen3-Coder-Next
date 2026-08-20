"""Append-only memory observability built on the existing MemoryEvent contract."""

from __future__ import annotations

from typing import Any

from qwen3_coder_next.memory.policies import MemoryLifecycleAction, MemoryLifecycleActionType
from qwen3_coder_next.memory.schemas import MemoryEvent, MemoryItem
from qwen3_coder_next.memory.state import MemoryState


class MemoryAuditRecorder:
    """Record memory activity without changing lifecycle decisions or outcomes."""

    def record_event(self, state: MemoryState, event: MemoryEvent) -> MemoryState:
        """Append a validated event and return a new state snapshot."""

        self._ensure_state(state)
        if not isinstance(event, MemoryEvent):
            raise ValueError("event must be a MemoryEvent instance.")
        return state.append_memory_event(event)

    def record_memory_write(
        self,
        state: MemoryState,
        memory: MemoryItem,
        *,
        operation: str = "write",
        actor: str = "memory",
    ) -> MemoryState:
        """Record a memory write with the complete memory snapshot as payload."""

        self._ensure_state(state)
        if not isinstance(memory, MemoryItem):
            raise ValueError("memory must be a MemoryItem instance.")
        if not isinstance(operation, str) or not operation.strip():
            raise ValueError("operation must be a non-empty string.")
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("actor must be a non-empty string.")
        event = MemoryEvent(
            event_type=f"memory_{operation}",
            actor=actor,
            payload={"memory": memory.to_dict(), "operation": operation},
            references=(memory.memory_id, *memory.references),
        )
        return state.append_memory_event(event)

    def record_memory_read(
        self,
        state: MemoryState,
        memory: MemoryItem,
        *,
        actor: str = "memory",
    ) -> MemoryState:
        """Record a memory read without changing the memory payload."""

        return self.record_memory_write(state, memory, operation="read", actor=actor)

    def record_lifecycle_action(
        self,
        state: MemoryState,
        action: MemoryLifecycleAction,
        *,
        actor: str = "memory_policy_engine",
    ) -> MemoryState:
        """Record an already-selected promotion or eviction action."""

        self._ensure_state(state)
        if not isinstance(action, MemoryLifecycleAction):
            raise ValueError("action must be a MemoryLifecycleAction instance.")
        if not isinstance(actor, str) or not actor.strip():
            raise ValueError("actor must be a non-empty string.")
        event_type = (
            "memory_promoted"
            if action.action is MemoryLifecycleActionType.PROMOTE
            else "memory_evicted"
        )
        payload: dict[str, Any] = {
            "memory": action.memory.to_dict(),
            "reason": action.reason,
            "target_tier": action.target_tier.value if action.target_tier else None,
        }
        event = MemoryEvent(
            event_type=event_type,
            actor=actor,
            payload=payload,
            references=(action.memory.memory_id, *action.memory.references),
        )
        return state.append_memory_event(event)

    @staticmethod
    def _ensure_state(state: MemoryState) -> None:
        if not isinstance(state, MemoryState):
            raise ValueError("state must be a MemoryState instance.")
