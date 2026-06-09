"""Smoke tests for the memory foundation."""

import unittest

from qwen3_coder_next.memory import (
    DuplicateMemoryError,
    MemoryEntry,
    MemoryKind,
    MemoryManager,
    MemoryNotFoundError,
    MemoryStore,
)


class MemoryFoundationSmokeTest(unittest.TestCase):
    """Verify memory contracts, store, and manager behavior."""

    def test_memory_contracts_can_be_created(self) -> None:
        """Create the memory contract objects."""

        memory = MemoryEntry(
            memory_id="memory-001",
            kind=MemoryKind.WORKING,
            content="Remember the current step.",
        )

        self.assertEqual(memory.memory_id, "memory-001")
        self.assertEqual(memory.kind, MemoryKind.WORKING)
        self.assertEqual(memory.content, "Remember the current step.")

    def test_memory_store_lifecycle(self) -> None:
        """Create, retrieve, update, list, and delete memories."""

        store = MemoryStore()
        memory = MemoryEntry(
            memory_id="memory-002",
            kind=MemoryKind.EPISODIC,
            content="Initial memory content.",
        )

        created = store.create_memory(memory)
        updated = store.update_memory(
            MemoryEntry(
                memory_id="memory-002",
                kind=MemoryKind.EPISODIC,
                content="Updated memory content.",
            )
        )

        self.assertEqual(created, memory)
        self.assertEqual(store.get_memory("memory-002"), updated)
        self.assertEqual(store.list_memories(), [updated])

        store.delete_memory("memory-002")
        self.assertEqual(store.list_memories(), [])

    def test_duplicate_and_missing_memory_handling(self) -> None:
        """Raise the expected exceptions for duplicate and missing memories."""

        store = MemoryStore()
        memory = MemoryEntry(
            memory_id="memory-003",
            kind=MemoryKind.FACT,
            content="Fact memory.",
        )

        store.create_memory(memory)

        with self.assertRaises(DuplicateMemoryError):
            store.create_memory(memory)

        with self.assertRaises(MemoryNotFoundError):
            store.get_memory("missing")

        with self.assertRaises(MemoryNotFoundError):
            store.update_memory(
                MemoryEntry(
                    memory_id="missing",
                    kind=MemoryKind.FACT,
                    content="Missing memory.",
                )
            )

        with self.assertRaises(MemoryNotFoundError):
            store.delete_memory("missing")

    def test_memory_manager_wraps_store_operations(self) -> None:
        """Use the manager to proxy store operations."""

        manager = MemoryManager()
        memory = MemoryEntry(
            memory_id="memory-004",
            kind=MemoryKind.WORKING,
            content="Managed memory.",
        )

        manager.create_memory(memory)
        self.assertEqual(manager.get_memory("memory-004"), memory)
        self.assertEqual(manager.list_memories(), [memory])
