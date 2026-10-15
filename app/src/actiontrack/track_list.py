"""`actiontrack list`: filter, order and render stored items."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import date
from typing import Literal, Sequence

from .core_models import Item, Person, is_overdue
from .core_store import Store
from .track_owner_lookup import lookup_owner

_MAX_TASK = 60


@dataclass
class ListResult:
    items: list[Item]
    status: Literal["ok", "ambiguous_owner", "owner_not_found"]
    candidates: tuple[Person, ...] = field(default=())


def list_items(store: Store, today: date, owner: str | None = None,
               status: Literal["open", "done", "overdue"] | None = None,
               due_before: date | None = None) -> ListResult:
    owner_key = None
    if owner is not None:
        r = lookup_owner(owner, store.owners())
        if r.status == "ambiguous":
            return ListResult([], "ambiguous_owner", r.candidates)
        if r.status == "not_found":
            return ListResult([], "owner_not_found")
        owner_key = "unassigned" if r.status == "unassigned" else r.person.key
    items = store.query(owner_key=owner_key, status="open" if status == "overdue" else status,
                        due_before=due_before)
    if status == "overdue":
        items = [i for i in items if is_overdue(i, today)]
    items.sort(key=lambda i: (not is_overdue(i, today), i.due_date is None, i.due_date or date.min, i.id))
    return ListResult(items, "ok")


def _status(i: Item, today: date) -> str:
    return "overdue" if is_overdue(i, today) else i.status


def _cut(task: str) -> str:
    task = " ".join(task.split())
    return task if len(task) <= _MAX_TASK else task[:_MAX_TASK - 1] + "…"


def format_table(items: Sequence[Item], today: date) -> str:
    if not items:
        return "No items match"
    rows = [("ID", "OWNER", "TASK", "DUE", "STATUS", "SOURCE")]
    for i in items:
        src = os.path.basename(i.source_file) + (f" (+{len(i.also_seen_in)})" if i.also_seen_in else "")
        rows.append((str(i.id), i.owner.name if i.owner else "(unassigned)", _cut(i.task),
                     i.due_date.isoformat() if i.due_date else "—", _status(i, today), src))
    widths = [max(len(r[c]) for r in rows) for c in range(6)]
    return "\n".join("  ".join(v.ljust(w) for v, w in zip(r, widths)).rstrip() for r in rows)
