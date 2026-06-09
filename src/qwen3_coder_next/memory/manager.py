"""Stable API layer for memory management."""

from qwen3_coder_next.logging import get_logger
from qwen3_coder_next.memory.contracts import MemoryEntry
from qwen3_coder_next.memory.store import MemoryStore


class MemoryManager:
    """Manage memory operations through a store and logger."""

    def __init__(self, store: MemoryStore | None = None) -> None:
        """Initialize the memory manager with an in-memory store."""

        self._store = store or MemoryStore()
        self._logger = get_logger("qwen3_coder_next.memory")

    def create_memory(self, memory: MemoryEntry) -> MemoryEntry:
        """Create and log a new memory entry."""

        self._logger.info("Creating memory for memory_id=%s", memory.memory_id)
        return self._store.create_memory(memory)

    def get_memory(self, memory_id: str) -> MemoryEntry:
        """Retrieve and log a memory lookup."""

        self._logger.info("Retrieving memory for memory_id=%s", memory_id)
        return self._store.get_memory(memory_id)

    def update_memory(self, memory: MemoryEntry) -> MemoryEntry:
        """Update and log an existing memory entry."""

        self._logger.info("Updating memory for memory_id=%s", memory.memory_id)
        return self._store.update_memory(memory)

    def delete_memory(self, memory_id: str) -> None:
        """Delete and log a memory entry."""

        self._logger.info("Deleting memory for memory_id=%s", memory_id)
        self._store.delete_memory(memory_id)

    def list_memories(self) -> list[MemoryEntry]:
        """List and log all stored memories."""

        self._logger.info("Listing all memories")
        return self._store.list_memories()
