"""`actiontrack done <id>`: mark one stored item done (database only)."""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from .core_models import Item
from .core_store import Store


@dataclass(frozen=True)
class DoneResult:
    outcome: Literal["done", "already_done", "not_found"]
    item: Item | None
    message: str


def mark_done(store: Store, item_id: int, now: datetime) -> DoneResult:
    outcome = store.mark_done(item_id, now)
    if outcome == "not_found":
        return DoneResult(outcome, None, f"No item with id {item_id}")
    item = store.get(item_id)
    if outcome == "already_done":
        return DoneResult(outcome, item, f"#{item_id} was already done")
    return DoneResult(outcome, item, f"Marked #{item_id} done: {item.task}")
