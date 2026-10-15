"""Orchestrates `actiontrack followup <owner>`: resolve owner, compose, create a draft, report.

Only ever calls `gateway.create_draft`; the store is read-only here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from .core_models import DraftResult, OK, Person, RUNTIME_ERROR, USAGE_ERROR, is_overdue
from .core_store import Store
from .followup_compose import compose
from .followup_gmail_draft import DraftGateway
from .track_owner_lookup import lookup_owner


@dataclass
class FollowupOutcome:
    exit_code: int
    message: str
    candidates: tuple[Person, ...] = ()
    draft_result: DraftResult | None = None
    included_ids: tuple[int, ...] = field(default=())


def _who(p: Person) -> str:
    return f"{p.name} <{p.email}>" if p.email else p.name


def run_followup(owner_query: str, store: Store, gateway: DraftGateway, today: date,
                 no_recipient: bool = False) -> FollowupOutcome:
    found = lookup_owner(owner_query, store.owners())
    if found.status == "ambiguous":
        lines = "\n".join(f"  {_who(p)}" for p in found.candidates)
        return FollowupOutcome(
            USAGE_ERROR, f"'{owner_query}' matches several owners:\n{lines}\n"
            "Retype with the full name or email.", candidates=found.candidates)
    if found.status == "not_found":
        return FollowupOutcome(USAGE_ERROR, f"No owner matches '{owner_query}'")
    if found.status == "unassigned":
        return FollowupOutcome(
            USAGE_ERROR, "Unassigned items have no recipient; assign an owner in the notes")
    person = found.person

    items = store.query(owner_key=person.key, status="open")
    draft = compose(person, items, today)
    if draft is None:
        return FollowupOutcome(OK, f"Nothing to follow up for {person.name}")
    if draft.to is None and not no_recipient:
        return FollowupOutcome(
            RUNTIME_ERROR, f"{person.name} has no email address in any note; "
            "use --no-recipient to create a draft anyway")

    result = gateway.create_draft(draft)  # AppError propagates (exit 1)

    by_id = {i.id: i for i in items}
    lines = []
    for iid in draft.included_ids:
        i = by_id[iid]
        due = f"due {i.due_date.isoformat()}" if i.due_date else "no due date"
        lines.append(f"  #{iid} {' '.join(i.task.split())} — {due}" + (" (overdue)" if is_overdue(i, today) else ""))
    head = ("Dry run: no draft was created." if result.draft_id == "dry-run"
            else f"Draft created for {_who(person)}: id {result.draft_id}" + (f" ({result.link})" if result.link else ""))
    msg = [head, "Items included:", *lines]
    unassigned = len(store.query(owner_key="unassigned", status="open"))
    if unassigned:
        msg.append(f"{unassigned} unassigned open item(s) not included (no recipient)")
    return FollowupOutcome(OK, "\n".join(msg), draft_result=result, included_ids=draft.included_ids)
