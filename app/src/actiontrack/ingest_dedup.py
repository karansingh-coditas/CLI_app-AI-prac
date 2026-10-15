"""What counts as the same action item, and how two occurrences merge (pure)."""
from __future__ import annotations

import unicodedata
from dataclasses import dataclass, replace

from .core_models import Issue, Item, Person


def normalise_task(task: str) -> str:
    kept = "".join(c for c in task.lower() if not unicodedata.category(c).startswith("P"))
    return " ".join(kept.split())


def dedup_key(owner: Person | None, task: str) -> str:
    return f"{owner.key if owner else '-'}|{normalise_task(task)}"


@dataclass(frozen=True)
class MergeResult:
    item: Item
    changed: bool
    issues: tuple[Issue, ...]


def _union(*lists: list[str]) -> list[str]:
    return list(dict.fromkeys(x for lst in lists for x in lst))


def merge(existing: Item, incoming: Item) -> MergeResult:
    done = existing.status == "done" or incoming.status == "done"
    if incoming.source_date < existing.source_date:
        primary, other = (incoming.source_file, incoming.source_date), existing.source_file
    else:
        primary, other = (existing.source_file, existing.source_date), incoming.source_file
    seen = [f for f in _union(existing.also_seen_in, incoming.also_seen_in, [other]) if f != primary[0]]

    dues = [d for d in (existing.due_date, incoming.due_date) if d]
    due = max(dues) if dues else None
    issues = ()
    if existing.due_date and due != existing.due_date:
        issues = (Issue(incoming.source_file, None, "DUE_CHANGED",
                        f"due date changed {existing.due_date} -> {due}: {existing.task}"),)

    merged = replace(
        existing,
        status="done" if done else "open",
        done_at=existing.done_at or (incoming.done_at if done else None),
        source_file=primary[0], source_date=primary[1],
        also_seen_in=seen, due_date=due,
        notes=_union(existing.notes, incoming.notes),
    )
    return MergeResult(merged, merged != existing, issues)
