from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from veil_garden.store import AliasStore


class StoreTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = AliasStore(":memory:")

    def tearDown(self) -> None:
        self.store.close()

    def test_add_and_read_alias(self) -> None:
        item = self.store.add({"address": "Leaf@Path.Example", "label": "Reading", "tags": ["weekly"]})
        self.assertEqual(item["address"], "leaf@path.example")
        self.assertEqual(self.store.get(item["id"])["label"], "Reading")

    def test_duplicate_address_is_rejected_case_insensitively(self) -> None:
        self.store.add({"address": "leaf@example.com"})
        with self.assertRaisesRegex(ValueError, "already"):
            self.store.add({"address": "LEAF@example.com"})

    def test_update_keeps_unspecified_values(self) -> None:
        item = self.store.add({"address": "leaf@example.com", "label": "Old", "note": "Keep"})
        updated = self.store.update(item["id"], {"label": "New", "status": "resting"})
        self.assertEqual(updated["address"], "leaf@example.com")
        self.assertEqual(updated["note"], "Keep")
        self.assertEqual(updated["status"], "resting")

    def test_invalid_status_is_rejected(self) -> None:
        with self.assertRaisesRegex(ValueError, "status"):
            self.store.add({"address": "leaf@example.com", "status": "deleted"})

    def test_remove_is_local_and_audited(self) -> None:
        item = self.store.add({"address": "leaf@example.com"})
        self.store.remove(item["id"])
        with self.assertRaises(KeyError):
            self.store.get(item["id"])
        self.assertEqual(self.store.events()[0]["kind"], "alias.removed")

    def test_import_counts_invalid_and_duplicate_records(self) -> None:
        result = self.store.import_many(
            [
                {"address": "one@example.com"},
                {"address": "ONE@example.com"},
                {"address": "invalid"},
                {"address": "two@example.com"},
            ]
        )
        self.assertEqual(result, {"imported": 2, "duplicates": 1, "invalid": 1})
        self.assertEqual([event["kind"] for event in self.store.events()], ["import.completed"])

    def test_import_limit_is_enforced(self) -> None:
        with self.assertRaisesRegex(ValueError, "5000"):
            self.store.import_many([{}] * 5001)

    def test_search_matches_label_note_and_tags(self) -> None:
        self.store.add(
            {"address": "one@example.com", "label": "Reading", "note": "Sunday", "tags": ["weekly"]}
        )
        self.assertEqual(len(self.store.list_aliases(query="Reading")), 1)
        self.assertEqual(len(self.store.list_aliases(query="Sunday")), 1)
        self.assertEqual(len(self.store.list_aliases(query="weekly")), 1)

    def test_status_filter_and_stats(self) -> None:
        self.store.add({"address": "one@example.com", "status": "active"})
        self.store.add({"address": "two@example.com", "status": "resting", "label": "Archive"})
        self.assertEqual(len(self.store.list_aliases(status="resting")), 1)
        self.assertEqual(self.store.stats(), {"total": 2, "active": 1, "resting": 1, "unlabeled": 1})

    def test_event_history_never_contains_address(self) -> None:
        self.store.add({"address": "secret.alias@example.com"})
        serialized = str(self.store.events())
        self.assertNotIn("secret.alias", serialized)

    def test_demo_seed_uses_reserved_domains(self) -> None:
        self.store.seed_demo()
        items = self.store.list_aliases(limit=10)
        self.assertEqual(len(items), 3)
        self.assertTrue(all(item["address"].endswith("@example.invalid") for item in items))

    def test_file_database_survives_restart(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "garden.sqlite3"
            first = AliasStore(path)
            first.add({"address": "leaf@example.com"})
            first.close()
            second = AliasStore(path)
            try:
                self.assertEqual(second.stats()["total"], 1)
            finally:
                second.close()


if __name__ == "__main__":
    unittest.main()
