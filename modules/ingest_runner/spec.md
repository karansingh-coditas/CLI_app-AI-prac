# ingest_runner — Spec

**Family:** `ingest_` · **File:** `src/actiontrack/ingest_runner.py`
**Depends on:** `core_models`, `core_store`, `ingest_note_parser`, `ingest_owner_resolver`, `ingest_date_resolver`, `ingest_dedup`

## Purpose
Orchestrate `actiontrack ingest <folder>`: read files, run the pipeline per note, persist, and produce the end-of-run report. Contains **no** parsing, date, owner or merge logic of its own.

## Requirements covered
FR-N4, FR-I1, FR-I3, FR-I4, FR-I5, FR-I6, FR-P3 (status), FR-E6, FR-E9, FR-E16–E19 (orchestration), NFR-2, NFR-3, NFR-4, NFR-5. Acceptance: AC-1, 2, 4, 5, 6, 12.

## Public interface

```python
@dataclass
class IngestReport:
    files_read: int; files_skipped: list[Issue]
    items_added: int; items_merged: int; items_updated: int
    items_unassigned: int; items_no_due: int; items_ambiguous: int
    issues: list[Issue]                      # warnings (unknown owner, bad due, due changed…)

def run_ingest(folder: str, store: Store, now: datetime) -> IngestReport   # AppError on fatal
def format_report(report: IngestReport) -> str
```

## Pipeline (per file, inside `store.atomic()`)
1. List `*.md` directly inside `folder` (no recursion), sorted by name (case-insensitive extension).
2. Read bytes → decode UTF-8 (with BOM tolerated). Decode/read failure → skip, `MALFORMED_NOTE`.
3. `parse_note` → on `MalformedNote` skip the file, record `Issue(code=MALFORMED_NOTE, reason)`, **store nothing** from it.
4. For each `RawItemLine`:
   1. `resolve_owner(line.text, note.attendees)` → owner / text / note.
   2. `resolve_due(owner_result.task_text, note.date)` → due / cleaned task / warning.
   3. If the cleaned task is empty, use `raw_text` as the task (FR-E18) and add `UNPARSEABLE_ITEM`.
   4. Build `Item` (`status = done if checked else open`, `done_at = now` when checked, `source_file`, `source_date = note.date`, `raw_text`, `notes`, `dedup_key = dedup_key(owner, task)`).
   5. `store.find_by_key(key)`: none → `store.add` (added++). Exists → `merge`; if `changed` → `store.update` (merged++ and updated++ when fields beyond `also_seen_in` changed; unchanged → no write).
5. Any unexpected exception inside one file rolls back that file's transaction, records an `Issue`, and continues with the next file (never crash, NFR-2).

## Counting rules
- `items_unassigned`: items in this run with no owner after resolution (includes ambiguous/unknown). `items_ambiguous` is the ambiguous subset. `items_no_due`: items with `due_date is None` after merge.
- Counts are for items **seen in this run**, not totals in the DB. Re-running on unchanged input → `added=0`, `merged=0`, `updated=0`.

## Failure / exit semantics
- Folder missing, not a directory, or unreadable → `AppError(exit_code=1)`.
- DB not writable → `AppError(exit_code=1)` (raised by `core_store`).
- Skipped notes never cause a non-zero exit (FR-I6, FR-E17).
- Source files are opened read-only and never modified (NFR-5).

## Report format (`format_report`)
```
Ingest complete: 4 files read, 1 skipped
  Items: 9 added, 2 merged (duplicates), 1 updated
  Needs attention: 2 unassigned (1 ambiguous owner), 3 with no due date
Skipped:
  notes/bad.md — missing front matter
Warnings:
  notes/a.md:12 — ambiguous owner: Priya (Priya Sharma | Priya Nair)
```
Warnings and skips are also written to stderr by `cli_app`; `format_report` only builds the text.

## Out of scope
Recursion, watching folders, deleting stale items, CLI parsing.

## Amendment (2026-10-15)
Each `Note.unrecognised` line becomes an `UNPARSEABLE_ITEM` warning ("possible action item is not a '- [ ]' checkbox line, not ingested"). Warnings are ordered by line within each file.
