"""Deterministic promotion and eviction policies for memory state."""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from enum import StrEnum

from qwen3_coder_next.memory.schemas import MemoryEvent, MemoryItem, MemoryTier
from qwen3_coder_next.memory.state import MemoryState


class MemoryLifecycleActionType(StrEnum):
    """Lifecycle action selected for a memory item."""

    PROMOTE = "promote"
    EVICT = "evict"


@dataclass(frozen=True, slots=True)
class MemoryLifecycleAction:
    """Immutable lifecycle decision for one memory item."""

    action: MemoryLifecycleActionType
    memory: MemoryItem
    target_tier: MemoryTier | None = None
    reason: str = ""


@dataclass(frozen=True, slots=True)
class MemoryLifecyclePlan:
    """Deterministic set of lifecycle actions for a state snapshot."""

    state_id: str
    as_of: datetime
    actions: tuple[MemoryLifecycleAction, ...] = ()


_TIER_ORDER = (MemoryTier.WORKING, MemoryTier.SESSION, MemoryTier.PROJECT, MemoryTier.GLOBAL)


def _next_tier(tier: MemoryTier) -> MemoryTier | None:
    """Return the next durable tier, if one exists."""

    try:
        return _TIER_ORDER[_TIER_ORDER.index(tier) + 1]
    except (ValueError, IndexError):
        return None


def _signal_matches(state: MemoryState, memory_id: str, signals: tuple[str, ...]) -> bool:
    """Match configured signals against events referencing the memory."""

    configured = set(signals)
    if not configured:
        return False
    return any(
        memory_id in event.references
        and event.event_type in configured
        for event in state.memory_events
    )


class MemoryPolicyEngine:
    """Apply deterministic retention, promotion, and eviction decisions."""

    def plan(self, state: MemoryState, *, as_of: datetime | None = None) -> MemoryLifecyclePlan:
        """Create lifecycle actions without mutating ``state``."""

        if not isinstance(state, MemoryState):
            raise ValueError("state must be a MemoryState instance.")
        policy = state.retention_policy
        effective_as_of = as_of or self._default_as_of(state)
        if not isinstance(effective_as_of, datetime):
            raise ValueError("as_of must be a datetime instance.")
        if policy is None:
            return MemoryLifecyclePlan(state_id=state.state_id, as_of=effective_as_of)

        cutoff = effective_as_of - timedelta(days=policy.keep_days)
        actions: list[MemoryLifecycleAction] = []
        for memory in state.memory_items:
            if memory.tier is not policy.tier:
                continue
            if _signal_matches(state, memory.memory_id, policy.prune_on_signal):
                actions.append(
                    MemoryLifecycleAction(
                        action=MemoryLifecycleActionType.EVICT,
                        memory=memory,
                        reason="prune signal matched",
                    )
                )
                continue
            target_tier = _next_tier(memory.tier)
            if target_tier is not None and _signal_matches(
                state, memory.memory_id, policy.promote_on_signal
            ):
                actions.append(
                    MemoryLifecycleAction(
                        action=MemoryLifecycleActionType.PROMOTE,
                        memory=memory,
                        target_tier=target_tier,
                        reason="promotion signal matched",
                    )
                )
                continue
            if memory.timestamp < cutoff:
                actions.append(
                    MemoryLifecycleAction(
                        action=MemoryLifecycleActionType.EVICT,
                        memory=memory,
                        reason="retention period expired",
                    )
                )
        return MemoryLifecyclePlan(state_id=state.state_id, as_of=effective_as_of, actions=tuple(actions))

    def apply(self, state: MemoryState, *, as_of: datetime | None = None) -> MemoryState:
        """Return a new state with the planned lifecycle actions applied."""

        plan = self.plan(state, as_of=as_of)
        if not plan.actions:
            return state
        evicted = {action.memory.memory_id for action in plan.actions if action.action is MemoryLifecycleActionType.EVICT}
        promotions = {
            action.memory.memory_id: action.target_tier
            for action in plan.actions
            if action.action is MemoryLifecycleActionType.PROMOTE and action.target_tier is not None
        }
        updated_items = tuple(
            replace(memory, tier=promotions[memory.memory_id])
            if memory.memory_id in promotions
            else memory
            for memory in state.memory_items
            if memory.memory_id not in evicted
        )
        revised = state.record_revision("memory lifecycle policy applied")
        for action in plan.actions:
            event_type = (
                "memory_promoted"
                if action.action is MemoryLifecycleActionType.PROMOTE
                else "memory_evicted"
            )
            revised = revised.append_memory_event(
                MemoryEvent(
                    event_type=event_type,
                    actor="memory_policy_engine",
                    payload={
                        "reason": action.reason,
                        "target_tier": action.target_tier.value if action.target_tier else None,
                    },
                    references=(action.memory.memory_id,),
                )
            )
        return replace(revised, memory_items=updated_items)

    @staticmethod
    def _default_as_of(state: MemoryState) -> datetime:
        """Choose a deterministic reference time from the state contents."""

        timestamps = [item.timestamp for item in state.memory_items]
        timestamps.append(state.updated_at)
        return max(timestamps, default=datetime.fromtimestamp(0, UTC))
