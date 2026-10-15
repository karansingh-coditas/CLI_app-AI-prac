"""Build the follow-up email Draft for one owner (pure: no Gmail, DB or clock)."""
from __future__ import annotations

import os
from datetime import date
from typing import Sequence

from .core_models import Draft, Item, Person, is_overdue


def _fmt(d: date) -> str:
    return f"{d:%a} {d.day} {d:%b %Y}"  # e.g. Fri 16 Oct 2026


def _line(i: Item, today: date) -> str:
    task = " ".join(i.task.split())
    stem = os.path.splitext(os.path.basename(i.source_file))[0]
    due = f"due {_fmt(i.due_date)}" if i.due_date else "no due date"
    late = ""
    if is_overdue(i, today):
        n = (today - i.due_date).days
        late = f" ({n} day{'s' if n != 1 else ''} overdue)"
    return f"- {task} — {due}{late} (from {stem}, {i.source_date.isoformat()})"


def compose(owner: Person, items: Sequence[Item], today: date) -> Draft | None:
    unique = {i.id: i for i in items if i.status == "open" and i.owner == owner}
    if not unique:
        return None
    ordered = sorted(unique.values(), key=lambda i: (i.due_date is None, i.due_date or date.min, i.id))
    sections = [("Overdue", [i for i in ordered if is_overdue(i, today)])]
    sections.append(("Open", [i for i in ordered if not is_overdue(i, today)]))
    sections = [(h, its) for h, its in sections if its]

    body = [f"Hi {owner.first_name},", "",
            "Here is a summary of your outstanding action items from our meetings:", ""]
    for heading, its in sections:
        body += [heading, *(_line(i, today) for i in its), ""]
    body += ["Please let me know if anything has changed or needs help.", "", "Thanks,"]
    return Draft(
        to=owner.email,
        subject=f"Action items follow-up — {owner.first_name} — {today.isoformat()}",
        body="\n".join(body),
        included_ids=tuple(i.id for _, its in sections for i in its),
    )
