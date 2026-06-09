"""Dictionary-backed in-memory memory storage."""

from qwen3_coder_next.memory.contracts import MemoryEntry
from qwen3_coder_next.memory.exceptions import DuplicateMemoryError, MemoryNotFoundError


class MemoryStore:
    """In-memory store for memory entries."""

    def __init__(self) -> None:
        """Initialize the in-memory memory store."""

        self._memories: dict[str, MemoryEntry] = {}

    def create_memory(self, memory: MemoryEntry) -> MemoryEntry:
        """Create a new memory entry."""

        if memory.memory_id in self._memories:
            raise DuplicateMemoryError(
                f"Memory already exists for memory_id={memory.memory_id!r}."
            )
        self._memories[memory.memory_id] = memory
        return memory

    def get_memory(self, memory_id: str) -> MemoryEntry:
        """Return a stored memory by memory identifier."""

        try:
            return self._memories[memory_id]
        except KeyError as exc:
            raise MemoryNotFoundError(f"Memory not found for memory_id={memory_id!r}.") from exc

    def update_memory(self, memory: MemoryEntry) -> MemoryEntry:
        """Replace an existing memory entry."""

        if memory.memory_id not in self._memories:
            raise MemoryNotFoundError(f"Memory not found for memory_id={memory.memory_id!r}.")
        self._memories[memory.memory_id] = memory
        return memory

    def delete_memory(self, memory_id: str) -> None:
        """Delete a stored memory by memory identifier."""

        if memory_id not in self._memories:
            raise MemoryNotFoundError(f"Memory not found for memory_id={memory_id!r}.")
        del self._memories[memory_id]

    def list_memories(self) -> list[MemoryEntry]:
        """Return all stored memories."""

        return list(self._memories.values())
