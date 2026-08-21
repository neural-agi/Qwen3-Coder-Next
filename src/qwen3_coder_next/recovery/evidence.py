"""Deterministic, read-only evidence capture for normalized failures."""
from __future__ import annotations

from collections.abc import Iterable

from qwen3_coder_next.recovery.contracts import EvidenceBundle, FailureEvent, _texts


class EvidenceCapture:
    """Build an evidence snapshot from explicitly supplied references and context."""

    def capture(
        self,
        event: FailureEvent,
        *,
        recent_actions: Iterable[str] = (),
        log_refs: Iterable[str] = (),
        command_output: Iterable[str] = (),
        memory_refs: Iterable[str] = (),
        file_anchors: Iterable[str] = (),
        agent_status: str = "",
        worktree_ref: str | None = None,
    ) -> EvidenceBundle:
        if not isinstance(event, FailureEvent):
            raise ValueError("event must be a FailureEvent.")
        if not isinstance(agent_status, str):
            raise ValueError("agent_status must be text.")
        selected_worktree = event.worktree_ref if worktree_ref is None else worktree_ref
        if not isinstance(selected_worktree, str):
            raise ValueError("worktree_ref must be text.")
        if event.worktree_ref and selected_worktree and selected_worktree != event.worktree_ref:
            raise ValueError("worktree_ref conflicts with the failure event.")
        # Capture only caller-provided references. No filesystem or external lookup occurs here.
        return EvidenceBundle(
            recent_actions=_texts(recent_actions, "recent_actions"),
            log_refs=_texts(log_refs, "log_refs"),
            command_output=_texts(command_output, "command_output"),
            memory_refs=_texts(memory_refs, "memory_refs"),
            file_anchors=_texts(file_anchors, "file_anchors"),
            worktree_ref=selected_worktree,
            agent_status=agent_status.strip(),
        )
