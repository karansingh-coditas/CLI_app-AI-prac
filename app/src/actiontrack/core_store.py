"""SQLite persistence for Items. The only module that touches sqlite3."""
from __future__ import annotations

import json
import sqlite3
from contextlib import contextmanager
from datetime import date, datetime
from typing import Iterator, Literal, Mapping

from .core_models import AppError, Item, Person, RUNTIME_ERROR

_SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    owner_key TEXT, owner_name TEXT, owner_email TEXT,
    task TEXT NOT NULL, raw_text TEXT NOT NULL,
    due_date TEXT, status TEXT NOT NULL,
    source_file TEXT NOT NULL, source_date TEXT NOT NULL,
    dedup_key TEXT NOT NULL,
    also_seen_in TEXT NOT NULL, notes TEXT NOT NULL,
    created_at TEXT, done_at TEXT
);
CREATE UNIQUE INDEX IF NOT EXISTS ux_items_dedup ON items(dedup_key);
CREATE INDEX IF NOT EXISTS ix_items_owner ON items(owner_key);
"""

_COLS = ("owner_key", "owner_name", "owner_email", "task", "raw_text", "due_date", "status",
         "source_file", "source_date", "dedup_key", "also_seen_in", "notes", "created_at", "done_at")


def default_db_path(cli_value: str | None, env: Mapping[str, str]) -> str:
    return cli_value or env.get("ACTIONTRACK_DB") or "./actiontrack.db"


def _iso(d: date | datetime | None) -> str | None:
    return d.isoformat() if d else None


def _row_to_item(r: sqlite3.Row) -> Item:
    return Item(
        id=r["id"],
        owner=Person(r["owner_name"], r["owner_email"]) if r["owner_name"] is not None else None,
        task=r["task"], raw_text=r["raw_text"],
        due_date=date.fromisoformat(r["due_date"]) if r["due_date"] else None,
        status=r["status"], source_file=r["source_file"],
        source_date=date.fromisoformat(r["source_date"]),
        dedup_key=r["dedup_key"],
        also_seen_in=json.loads(r["also_seen_in"]), notes=json.loads(r["notes"]),
        created_at=datetime.fromisoformat(r["created_at"]) if r["created_at"] else None,
        done_at=datetime.fromisoformat(r["done_at"]) if r["done_at"] else None,
    )


def _item_params(i: Item) -> tuple:
    o = i.owner
    return (
        o.key if o else None, o.name if o else None, o.email if o else None,
        i.task, i.raw_text, _iso(i.due_date), i.status, i.source_file,
        i.source_date.isoformat(), i.dedup_key,
        json.dumps(i.also_seen_in), json.dumps(i.notes), _iso(i.created_at), _iso(i.done_at),
    )


class Store:
    def __init__(self, path: str):
        self._depth = 0
        try:
            self._db = sqlite3.connect(path, isolation_level=None)
            self._db.row_factory = sqlite3.Row
            self._db.executescript(_SCHEMA)
            self._db.execute("PRAGMA user_version = 1")
        except sqlite3.Error as e:
            raise AppError(f"cannot open database {path!r}: {e}", RUNTIME_ERROR) from e

    @contextmanager
    def atomic(self) -> Iterator[None]:
        if self._depth:  # nested: join the outer transaction
            self._depth += 1
            try:
                yield
            finally:
                self._depth -= 1
            return
        self._db.execute("BEGIN")
        self._depth = 1
        try:
            yield
        except BaseException:
            self._db.execute("ROLLBACK")
            raise
        else:
            self._db.execute("COMMIT")
        finally:
            self._depth = 0

    def add(self, item: Item) -> Item:
        if item.created_at is None:
            item.created_at = datetime.now().replace(microsecond=0)
        cur = self._db.execute(
            f"INSERT INTO items ({', '.join(_COLS)}) VALUES ({', '.join('?' * len(_COLS))})",
            _item_params(item))
        item.id = cur.lastrowid
        return item

    def update(self, item: Item) -> None:
        sets = ", ".join(f"{c} = ?" for c in _COLS)
        self._db.execute(f"UPDATE items SET {sets} WHERE id = ?", (*_item_params(item), item.id))

    def get(self, item_id: int) -> Item | None:
        r = self._db.execute("SELECT * FROM items WHERE id = ?", (item_id,)).fetchone()
        return _row_to_item(r) if r else None

    def find_by_key(self, dedup_key: str) -> Item | None:
        r = self._db.execute("SELECT * FROM items WHERE dedup_key = ?", (dedup_key,)).fetchone()
        return _row_to_item(r) if r else None

    def query(self, owner_key: str | None = None, status: Literal["open", "done"] | None = None,
              due_before: date | None = None) -> list[Item]:
        where, args = [], []
        if owner_key == "unassigned":
            where.append("owner_key IS NULL")
        elif owner_key is not None:
            where.append("owner_key = ?")
            args.append(owner_key)
        if status:
            where.append("status = ?")
            args.append(status)
        if due_before:
            where.append("due_date IS NOT NULL AND due_date < ?")
            args.append(due_before.isoformat())
        sql = "SELECT * FROM items" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY id"
        return [_row_to_item(r) for r in self._db.execute(sql, args)]

    def owners(self) -> list[Person]:
        rows = self._db.execute(
            "SELECT DISTINCT owner_key, owner_name, owner_email FROM items "
            "WHERE owner_key IS NOT NULL ORDER BY owner_name")
        return [Person(r["owner_name"], r["owner_email"]) for r in rows]

    def mark_done(self, item_id: int, now: datetime) -> Literal["done", "already_done", "not_found"]:
        item = self.get(item_id)
        if item is None:
            return "not_found"
        if item.status == "done":
            return "already_done"
        self._db.execute("UPDATE items SET status='done', done_at=? WHERE id=?", (now.isoformat(), item_id))
        return "done"

    def close(self) -> None:
        self._db.close()
