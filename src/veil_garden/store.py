from __future__ import annotations

import json
import os
import sqlite3
import threading
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .security import clean_tags, clean_text, normalize_email

VALID_STATUSES = {"active", "resting"}
CATALOG_LIMIT = 5000


def utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


class AliasStore:
    def __init__(self, path: str | Path) -> None:
        self.path = str(path)
        if self.path != ":memory:":
            target = Path(self.path)
            target.parent.mkdir(parents=True, exist_ok=True)
            if os.name != "nt":
                target.parent.chmod(0o700)
        self._lock = threading.RLock()
        self._conn = sqlite3.connect(self.path, check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.execute("PRAGMA journal_mode = WAL")
        self._conn.execute("PRAGMA busy_timeout = 5000")
        self._migrate()
        if self.path != ":memory:" and os.name != "nt":
            Path(self.path).chmod(0o600)

    def close(self) -> None:
        with self._lock:
            self._conn.close()

    def _migrate(self) -> None:
        with self._lock, self._conn:
            self._conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS aliases (
                    id TEXT PRIMARY KEY,
                    address TEXT NOT NULL COLLATE NOCASE UNIQUE,
                    label TEXT NOT NULL DEFAULT '',
                    note TEXT NOT NULL DEFAULT '',
                    status TEXT NOT NULL CHECK(status IN ('active', 'resting')),
                    tags TEXT NOT NULL DEFAULT '[]',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE INDEX IF NOT EXISTS aliases_status_idx ON aliases(status);
                CREATE INDEX IF NOT EXISTS aliases_updated_idx ON aliases(updated_at DESC);
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    kind TEXT NOT NULL,
                    detail TEXT NOT NULL,
                    created_at TEXT NOT NULL
                );
                """
            )

    @staticmethod
    def _payload(data: dict[str, Any], *, existing: dict[str, Any] | None = None) -> dict[str, Any]:
        base = existing or {}
        address = normalize_email(data.get("address", base.get("address", "")))
        label = clean_text(data.get("label", base.get("label", "")), limit=80)
        note = clean_text(data.get("note", base.get("note", "")), limit=500)
        status = clean_text(data.get("status", base.get("status", "active")), limit=16).lower()
        if status not in VALID_STATUSES:
            raise ValueError("invalid status")
        tags = clean_tags(data.get("tags", base.get("tags", [])))
        return {"address": address, "label": label, "note": note, "status": status, "tags": tags}

    @staticmethod
    def _row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        item["tags"] = json.loads(item["tags"] or "[]")
        return item

    def _event(self, kind: str, detail: str) -> None:
        self._conn.execute(
            "INSERT INTO events(kind, detail, created_at) VALUES (?, ?, ?)",
            (clean_text(kind, limit=32), clean_text(detail, limit=160), utc_now()),
        )
        self._conn.execute(
            "DELETE FROM events WHERE id NOT IN (SELECT id FROM events ORDER BY id DESC LIMIT 200)"
        )

    def add(self, data: dict[str, Any]) -> dict[str, Any]:
        item = self._payload(data)
        now = utc_now()
        alias_id = uuid.uuid4().hex[:16]
        try:
            with self._lock, self._conn:
                if self._conn.execute("SELECT COUNT(*) FROM aliases").fetchone()[0] >= CATALOG_LIMIT:
                    raise ValueError(f"catalog can contain at most {CATALOG_LIMIT} records")
                self._conn.execute(
                    """INSERT INTO aliases(id, address, label, note, status, tags, created_at, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        alias_id,
                        item["address"],
                        item["label"],
                        item["note"],
                        item["status"],
                        json.dumps(item["tags"], ensure_ascii=False),
                        now,
                        now,
                    ),
                )
                self._event("alias.added", "添入一枚本地地址")
        except sqlite3.IntegrityError as exc:
            raise ValueError("address already exists") from exc
        return self.get(alias_id)

    def get(self, alias_id: str) -> dict[str, Any]:
        with self._lock:
            row = self._conn.execute("SELECT * FROM aliases WHERE id = ?", (alias_id,)).fetchone()
        if row is None:
            raise KeyError(alias_id)
        return self._row(row)

    def update(self, alias_id: str, data: dict[str, Any]) -> dict[str, Any]:
        current = self.get(alias_id)
        item = self._payload(data, existing=current)
        try:
            with self._lock, self._conn:
                result = self._conn.execute(
                    """UPDATE aliases SET address=?, label=?, note=?, status=?, tags=?, updated_at=?
                    WHERE id=?""",
                    (
                        item["address"],
                        item["label"],
                        item["note"],
                        item["status"],
                        json.dumps(item["tags"], ensure_ascii=False),
                        utc_now(),
                        alias_id,
                    ),
                )
                if not result.rowcount:
                    raise KeyError(alias_id)
                self._event("alias.updated", "整理了一枚本地地址")
        except sqlite3.IntegrityError as exc:
            raise ValueError("address already exists") from exc
        return self.get(alias_id)

    def remove(self, alias_id: str) -> None:
        with self._lock, self._conn:
            result = self._conn.execute("DELETE FROM aliases WHERE id = ?", (alias_id,))
            if not result.rowcount:
                raise KeyError(alias_id)
            self._event("alias.removed", "移除了一条本地记录")

    def import_many(self, rows: list[dict[str, Any]]) -> dict[str, int]:
        if len(rows) > CATALOG_LIMIT:
            raise ValueError(f"an import can contain at most {CATALOG_LIMIT} records")
        prepared: list[dict[str, Any]] = []
        invalid = 0
        for row in rows:
            try:
                prepared.append(self._payload(row))
            except ValueError:
                invalid += 1
        imported = duplicates = 0
        now = utc_now()
        with self._lock, self._conn:
            current = self._conn.execute("SELECT COUNT(*) FROM aliases").fetchone()[0]
            for item in prepared:
                if current + imported >= CATALOG_LIMIT:
                    exists = self._conn.execute(
                        "SELECT 1 FROM aliases WHERE address = ?", (item["address"],)
                    ).fetchone()
                    if exists:
                        duplicates += 1
                        continue
                    raise ValueError(f"catalog can contain at most {CATALOG_LIMIT} records")
                try:
                    self._conn.execute(
                        """INSERT INTO aliases(id, address, label, note, status, tags, created_at, updated_at)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            uuid.uuid4().hex[:16],
                            item["address"],
                            item["label"],
                            item["note"],
                            item["status"],
                            json.dumps(item["tags"], ensure_ascii=False),
                            now,
                            now,
                        ),
                    )
                    imported += 1
                except sqlite3.IntegrityError:
                    duplicates += 1
            self._event(
                "import.completed",
                f"导入 {imported} 条；跳过 {duplicates} 条重复与 {invalid} 条无效记录",
            )
        return {"imported": imported, "duplicates": duplicates, "invalid": invalid}

    def list_aliases(
        self, *, query: str = "", status: str = "all", limit: int = 100, offset: int = 0
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []
        query = clean_text(query, limit=120)
        if query:
            where.append("(address LIKE ? OR label LIKE ? OR note LIKE ? OR tags LIKE ?)")
            needle = f"%{query}%"
            params.extend([needle, needle, needle, needle])
        if status in VALID_STATUSES:
            where.append("status = ?")
            params.append(status)
        sql = "SELECT * FROM aliases"
        if where:
            sql += " WHERE " + " AND ".join(where)
        sql += " ORDER BY updated_at DESC, address ASC LIMIT ? OFFSET ?"
        params.extend([max(1, min(limit, 500)), max(0, offset)])
        with self._lock:
            rows = self._conn.execute(sql, params).fetchall()
        return [self._row(row) for row in rows]

    def stats(self) -> dict[str, int]:
        with self._lock:
            rows = self._conn.execute("SELECT status, COUNT(*) AS n FROM aliases GROUP BY status").fetchall()
            unlabeled = self._conn.execute("SELECT COUNT(*) FROM aliases WHERE label = ''").fetchone()[0]
        counts = {row["status"]: row["n"] for row in rows}
        total = sum(counts.values())
        return {
            "total": total,
            "active": counts.get("active", 0),
            "resting": counts.get("resting", 0),
            "unlabeled": unlabeled,
        }

    def events(self, *, limit: int = 30) -> list[dict[str, Any]]:
        with self._lock:
            rows = self._conn.execute(
                "SELECT kind, detail, created_at FROM events ORDER BY id DESC LIMIT ?",
                (max(1, min(limit, 100)),),
            ).fetchall()
        return [dict(row) for row in rows]

    def seed_demo(self) -> None:
        if self.stats()["total"]:
            return
        examples = [
            {
                "address": "fern.path@example.invalid",
                "label": "Newsletter",
                "note": "A synthetic record for the demo garden.",
                "status": "active",
                "tags": ["reading", "demo"],
            },
            {
                "address": "quiet.lantern@example.invalid",
                "label": "Travel",
                "note": "Reserved example data; it never receives mail.",
                "status": "active",
                "tags": ["travel"],
            },
            {
                "address": "old.harbor@example.invalid",
                "label": "Archive",
                "note": "Resting locally; Apple state is not changed by this app.",
                "status": "resting",
                "tags": ["archive"],
            },
        ]
        self.import_many(examples)
