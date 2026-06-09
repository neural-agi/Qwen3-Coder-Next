"""Dictionary-backed memory storage with optional filesystem persistence."""

import json
from pathlib import Path

from qwen3_coder_next.memory.contracts import MemoryEntry, MemoryKind
from qwen3_coder_next.memory.exceptions import DuplicateMemoryError, MemoryNotFoundError


class MemoryStore:
    """Store for memory entries."""

    def __init__(self, storage_path: Path | None = None) -> None:
        """Initialize the memory store."""

        self._storage_path = storage_path
        self._memories: dict[str, MemoryEntry] = {}
        self._load_from_disk()

    def create_memory(self, memory: MemoryEntry) -> MemoryEntry:
        """Create a new memory entry."""

        if memory.memory_id in self._memories:
            raise DuplicateMemoryError(
                f"Memory already exists for memory_id={memory.memory_id!r}."
            )
        self._memories[memory.memory_id] = memory
        self._save_to_disk()
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
        self._save_to_disk()
        return memory

    def delete_memory(self, memory_id: str) -> None:
        """Delete a stored memory by memory identifier."""

        if memory_id not in self._memories:
            raise MemoryNotFoundError(f"Memory not found for memory_id={memory_id!r}.")
        del self._memories[memory_id]
        self._save_to_disk()

    def list_memories(self) -> list[MemoryEntry]:
        """Return all stored memories."""

        return list(self._memories.values())

    def _load_from_disk(self) -> None:
        """Load persisted memory entries if a storage path is configured."""

        if self._storage_path is None or not self._storage_path.exists():
            return

        with self._storage_path.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)

        self._memories = {
            item["memory_id"]: MemoryEntry(
                memory_id=str(item["memory_id"]),
                kind=MemoryKind(str(item["kind"])),
                content=str(item["content"]),
                metadata=dict(item.get("metadata", {})),
            )
            for item in payload
        }

    def _save_to_disk(self) -> None:
        """Persist memory entries if a storage path is configured."""

        if self._storage_path is None:
            return

        self._storage_path.parent.mkdir(parents=True, exist_ok=True)
        with self._storage_path.open("w", encoding="utf-8") as handle:
            json.dump([self._serialize_memory(memory) for memory in self._memories.values()], handle, indent=2)

    def _serialize_memory(self, memory: MemoryEntry) -> dict[str, object]:
        return {
            "memory_id": memory.memory_id,
            "kind": memory.kind.value,
            "content": memory.content,
            "metadata": memory.metadata,
        }
