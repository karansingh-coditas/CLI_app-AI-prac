"""Orchestrates `actiontrack ingest <folder>`: read notes, run the pipeline, persist, report.

Holds no parsing, date, owner or merge logic of its own.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime

from .core_models import AppError, Issue, Item, MalformedNote, Note, RUNTIME_ERROR
from .core_store import Store
from .ingest_date_resolver import resolve_due
from .ingest_dedup import dedup_key, merge
from .ingest_note_parser import parse_note
from .ingest_owner_resolver import resolve_owner


@dataclass
class IngestReport:
    files_read: int = 0
    files_skipped: list[Issue] = field(default_factory=list)
    items_added: int = 0
    items_merged: int = 0
    items_updated: int = 0
    items_unassigned: int = 0
    items_no_due: int = 0
    items_ambiguous: int = 0
    issues: list[Issue] = field(default_factory=list)


@dataclass
class _FileResult:
    added: int = 0
    merged: int = 0
    updated: int = 0
    unassigned: set[int] = field(default_factory=set)
    ambiguous: set[int] = field(default_factory=set)
    no_due: set[int] = field(default_factory=set)
    issues: list[Issue] = field(default_factory=list)


def _build_item(path: str, note: Note, line, now: datetime, res: _FileResult) -> Item:
    owner = resolve_owner(line.text, note.attendees)
    due = resolve_due(owner.task_text, note.date)
    task = due.task_text
    if owner.status == "ambiguous":
        res.issues.append(Issue(path, line.line_no, "AMBIGUOUS_OWNER", owner.note))
    elif owner.status == "unknown":
        res.issues.append(Issue(path, line.line_no, "UNKNOWN_OWNER", owner.note))
    if due.warning:
        res.issues.append(Issue(path, line.line_no, "BAD_DUE_DATE", due.warning))
    if not task:
        task = line.text
        res.issues.append(Issue(path, line.line_no, "UNPARSEABLE_ITEM",
                                f"nothing left of the task after parsing: {line.text!r}"))
    return Item(
        id=None, owner=owner.owner, task=task, raw_text=line.text, due_date=due.due,
        status="done" if line.checked else "open", source_file=path, source_date=note.date,
        dedup_key=dedup_key(owner.owner, task), also_seen_in=[],
        notes=[owner.note] if owner.note else [], done_at=now if line.checked else None,
    )


def _ingest_note(path: str, note: Note, store: Store, now: datetime) -> _FileResult:
    res = _FileResult()
    for line in note.unrecognised:  # reported so nothing is silently dropped (success criterion)
        res.issues.append(Issue(path, line.line_no, "UNPARSEABLE_ITEM",
                                f"possible action item is not a '- [ ]' checkbox line, not ingested: {line.text}"))
    for line in note.lines:
        item = _build_item(path, note, line, now, res)
        existing = store.find_by_key(item.dedup_key)
        if existing is None:
            item = store.add(item)
            res.added += 1
        else:
            m = merge(existing, item)
            res.issues.extend(m.issues)
            item = m.item
            if m.changed:
                store.update(item)
                res.merged += 1
                if (item.status, item.due_date, item.notes) != (existing.status, existing.due_date, existing.notes):
                    res.updated += 1
        if item.owner is None:
            res.unassigned.add(item.id)
            if any(n.startswith("ambiguous owner") for n in item.notes):
                res.ambiguous.add(item.id)
        if item.due_date is None:
            res.no_due.add(item.id)
    res.issues.sort(key=lambda i: i.line or 0)  # file order in the report; line-less ones (due changes) first
    return res


def run_ingest(folder: str, store: Store, now: datetime) -> IngestReport:
    if not os.path.isdir(folder):
        raise AppError(f"folder not found or not a directory: {folder}", RUNTIME_ERROR)
    try:
        names = sorted((n for n in os.listdir(folder) if n.lower().endswith(".md")), key=str.lower)
    except OSError as e:
        raise AppError(f"cannot read folder {folder}: {e}", RUNTIME_ERROR) from e

    report = IngestReport()
    unassigned: set[int] = set()
    ambiguous: set[int] = set()
    no_due: set[int] = set()
    for name in names:
        path = os.path.normpath(os.path.join(folder, name))
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "rb") as f:
                text = f.read().decode("utf-8-sig")
            note = parse_note(path, text)
            with store.atomic():
                res = _ingest_note(path, note, store, now)
        except MalformedNote as e:
            report.files_skipped.append(Issue(path, None, "MALFORMED_NOTE", e.reason))
            continue
        except UnicodeDecodeError:
            report.files_skipped.append(Issue(path, None, "MALFORMED_NOTE", "not valid UTF-8"))
            continue
        except Exception as e:  # one bad file must never stop the run; its transaction is rolled back
            report.files_skipped.append(
                Issue(path, None, "MALFORMED_NOTE", f"unexpected error: {type(e).__name__}: {e}"))
            continue
        report.files_read += 1
        report.items_added += res.added
        report.items_merged += res.merged
        report.items_updated += res.updated
        report.issues.extend(res.issues)
        unassigned |= res.unassigned
        ambiguous |= res.ambiguous
        no_due |= res.no_due
    no_due = {i for i in no_due if store.get(i).due_date is None}  # a later note may have supplied a date
    report.items_unassigned, report.items_ambiguous, report.items_no_due = len(unassigned), len(ambiguous), len(no_due)
    return report


def format_report(r: IngestReport) -> str:
    out = [
        f"Ingest complete: {r.files_read} files read, {len(r.files_skipped)} skipped",
        f"  Items: {r.items_added} added, {r.items_merged} merged (duplicates), {r.items_updated} updated",
        f"  Needs attention: {r.items_unassigned} unassigned ({r.items_ambiguous} ambiguous owner), "
        f"{r.items_no_due} with no due date",
    ]
    if r.files_skipped:
        out.append("Skipped:")
        out += [f"  {i.file} — {i.message}" for i in r.files_skipped]
    if r.issues:
        out.append("Warnings:")
        out += [f"  {i.file}{':' + str(i.line) if i.line else ''} — {i.message}" for i in r.issues]
    return "\n".join(out)
