# actiontrack — Requirements Specification

| | |
|---|---|
| **Version** | 1.0 (draft for review) |
| **Date** | 2026-10-15 |
| **Source** | `statement.rtf` + stakeholder answers (see §12) |

## 1. Background and Problem

Team meeting notes accumulate as markdown files. Action items inside them get lost, and follow-up emails are written late or not at all.

## 2. Goal

A small command-line tool, **actiontrack**, that:

1. reads meeting notes and extracts action items,
2. tracks each item's status over time, and
3. drafts follow-up emails (Gmail drafts) for a human to review.

**Success criteria**

- No action item written in a note is silently dropped.
- Any owner's open and overdue items can be listed in one command.
- A reviewable follow-up draft per owner can be produced in one command.
- Nothing is ever sent automatically.

## 3. Scope

**In scope:** the four CLI commands (§6), note parsing, local persistence, Gmail draft creation via the Gmail MCP connector, handling of the listed edge cases.

**Out of scope (v1):**

- Sending email (explicitly forbidden).
- Editing or re-writing the source `.md` files, including ticking `[x]` in them.
- Multi-user or shared databases, a web UI, notifications or reminders, calendar integration.
- Parsing formats other than `.md`.
- Natural-language understanding beyond the date phrases in §5.3.

## 4. Users and Stakeholders

| Role | Interest |
|---|---|
| Team member / meeting owner | Runs the CLI to ingest notes, check items and mark them done |
| Action-item owner (email recipient) | Receives a follow-up email after the sender reviews and sends the draft |

## 5. Data Requirements

### 5.1 Meeting note format (input)

Each `.md` file is one meeting. It has **YAML front matter** followed by a free-form body.

```markdown
---
date: 2026-10-12
attendees:
  - Priya Sharma <priya.sharma@example.com>
  - Priya Nair <priya.nair@example.com>
  - Rahul Mehta <rahul@example.com>
---

Free-form discussion text...

- [ ] Priya to send the revised quote by Friday
- [x] Rahul to share the deck
- [ ] Update the onboarding doc
```

- **FR-N1** `date` is required, in ISO `YYYY-MM-DD`. It is the *meeting date*, the anchor for resolving relative due dates.
- **FR-N2** `attendees` is required (list, at least one). Each entry is `Full Name <email>`. The email is optional per entry. An attendee without an email can still own items but cannot get a draft (see FR-F7).
- **FR-N3** Action items are body lines matching `- [ ] <text>` (open) or `- [x] <text>` (done, case-insensitive `x`). Other lines are ignored.
- **FR-N4** Only `.md` files are read. Subfolders are not scanned in v1 (see §11, Q-3).

### 5.2 Action item (stored record)

| Field | Description |
|---|---|
| `id` | Short, stable, human-typeable integer or code, unique. Used by `done <id>`. |
| `owner` | Resolved attendee (full name + email if known), or `NULL` if unassigned |
| `task` | Task text with the owner prefix and due-date phrase removed; original line kept in `raw_text` |
| `raw_text` | Original line, for audit and re-parsing |
| `due_date` | Real calendar date (`YYYY-MM-DD`), or `NULL` if none |
| `status` | `open` or `done` stored; `overdue` is **derived** (see FR-L3) |
| `source_file` | Path of the note the item came from |
| `source_date` | Meeting date of that note |
| `also_seen_in` | Other note(s) where the same item is repeated (see §7.1) |
| `created_at`, `done_at` | Timestamps |

### 5.3 Owner and due-date extraction

- **FR-P1 Owner.** Patterns such as `<Name> to <verb> …` or `<Name> will …`. The name is matched against the note's attendee list (see §7.3). If no name is found or it cannot be resolved, the item is **unassigned**.
- **FR-P2 Due date.** Phrases after `by` / `before` / `on` / `due`, or a trailing date, are resolved to a real date **relative to the meeting date**. Required support:
  - ISO dates (`2026-10-30`) and common written forms (`30 Oct`, `Oct 30`, `30 Oct 2026`)
  - weekday names (`Friday`) → the **next occurrence strictly after the meeting date**. Where the meeting itself falls on that weekday, it means one week later.
  - `today`, `tomorrow`, `next week` (the coming Monday), `end of week` (the Friday of the meeting week), `end of month`
  - Anything unparseable → `due_date = NULL`, with a warning in the ingest report. The raw phrase stays in `task` text.
- **FR-P3** A line marked `[x]` is ingested with status `done`.

## 6. Functional Requirements — CLI Commands

### 6.1 `actiontrack ingest <folder>`

- **FR-I1** Parse every `.md` file in `<folder>`; extract items per §5.
- **FR-I2** Persist items to the local SQLite database (default `./actiontrack.db`, overridable with `--db <path>` or env `ACTIONTRACK_DB`).
- **FR-I3** Ingest is **idempotent**. Re-running on the same folder must not create duplicates or reset the status of items already marked `done`.
- **FR-I4** A malformed note is **skipped and reported**. The run continues and never crashes (see §8).
- **FR-I5** At the end, print a summary:
  - files read, files skipped (with reason),
  - items added, duplicates merged, items updated,
  - items with no owner, items with no due date, ambiguous owners.
- **FR-I6** Exit code: `0` if the run completed (even with skipped files); non-zero only when the run could not execute at all (folder missing or unreadable, DB not writable).
- **FR-I7** If a later ingest sees an already-known item as `[x]`, mark it `done`. A later `[ ]` never re-opens an item that was marked done. This precedence rule is decided in §11, Q-4.

### 6.2 `actiontrack list`

- **FR-L1** Print items as a table: `id`, `owner`, `task`, `due`, `status`, `source`.
- **FR-L2** Filters (combinable with AND):
  - `--owner <name>`: case-insensitive; accepts a full name, or a first name when unambiguous. When the first name matches several people, list the candidates and exit non-zero (see §7.3).
  - `--status open|done|overdue`
  - `--due-before <date>`: ISO date. Items with no due date are excluded.
- **FR-L3** **Overdue** = status is `open`, a due date exists, and `due_date < today` (today's local date, an item due today is *not* overdue). The status filter `open` includes overdue items, since they are still open. `overdue` selects only the overdue subset. Output labels them `overdue`.
- **FR-L4** Unassigned and undated items appear in the list, shown as `—` (not hidden). Sort: overdue first, then by due date ascending, undated last.
- **FR-L5** Empty result prints a friendly "No items match", exit `0`.

### 6.3 `actiontrack done <id>`

- **FR-D1** Mark the item `done` and record `done_at`.
- **FR-D2** Unknown id → clear error, non-zero exit, no change.
- **FR-D3** Already-done item → no-op with an informational message, exit `0`.
- **FR-D4** Done state is stored in the database only, not written back to the `.md` file.

### 6.4 `actiontrack followup <owner>`

(The statement says "per owner". Interpreted as an argument selecting one owner. See §11, Q-5 for an `--all` alternative.)

- **FR-F1** Select the owner's **open and overdue** items, with overdue ones shown first and flagged.
- **FR-F2** Compose one email per owner, containing:
  - a greeting by first name,
  - a section "Overdue" and a section "Open", each item with task, due date and meeting/source,
  - items with no due date marked "no due date",
  - a polite closing.
- **FR-F3** Create the message as a **Gmail draft** through the Gmail MCP connector, with `To:` set to the owner's email from the note attendee list.
- **FR-F4** **The tool must never send an email.** Only the draft-creation operation is used. No code path calls a send operation. This is a hard requirement and must be covered by a test.
- **FR-F5** On success, print the draft id or link and the items included.
- **FR-F6** Owner with no open or overdue items → print "nothing to follow up", create no draft.
- **FR-F7** Owner has no known email → report clearly and create no draft. Fallback `--no-recipient` creates the draft with an empty `To:` (see §11, Q-6).
- **FR-F8** If the Gmail connector is unavailable or not authenticated → clear error and non-zero exit. No data is lost, and the command can be re-run.
- **FR-F9** Re-running `followup` creates a **new** draft each time (v1 does not de-duplicate drafts).
- **FR-F10** `--dry-run` prints the draft (subject, to, body) without calling Gmail. This is a recommended extra for review and testing.

## 7. Edge-Case Requirements

### 7.1 Duplicate items repeated across meetings

- **FR-E1** Two items are duplicates when they have the same **resolved owner** and the same **normalised task text** (lower-cased, punctuation and extra whitespace removed, owner prefix and due-date phrase stripped).
- **FR-E2** Duplicates are **merged into one record**, not stored twice. The record keeps the earliest source as the primary and lists the others in `also_seen_in`.
- **FR-E3** On merge:
  - if any occurrence is `[x]`, the item is `done`;
  - if due dates differ, keep the **latest** stated due date and note the change in the ingest report.
- **FR-E4** Duplicates within a single follow-up email or list output appear once.
- **FR-E5** Near-duplicates (reworded) are **not** merged in v1. Exact match after normalisation only (see §11, Q-7).

### 7.2 Items with no owner or no due date

- **FR-E6** Such items are **kept**, never dropped.
- **FR-E7** No owner → owner is `NULL` and displayed as `(unassigned)`. These items can be listed with `list --owner unassigned`. They are never included in a follow-up email (no recipient), and the `followup` summary reports the count of unassigned items so they are not forgotten.
- **FR-E8** No due date → `due_date = NULL`. These items are never "overdue" (an unknown deadline cannot be missed). They are shown in `open` lists and in follow-up emails as "no due date".
- **FR-E9** The ingest summary counts both categories (FR-I5).

### 7.3 Two people with the same first name

- **FR-E10** Ownership is resolved against the **attendee list of the note the item came from**.
- **FR-E11** If the item text uses a first name that matches exactly **one** attendee → that attendee is the owner.
- **FR-E12** If it matches **more than one** attendee (e.g. Priya Sharma and Priya Nair both attend) and the text does not disambiguate (no surname, initial or email) → the owner is **ambiguous**:
  - the item is stored as unassigned with the note `ambiguous owner: Priya (Priya Sharma | Priya Nair)`,
  - and is reported in the ingest summary.
  - Disambiguation hints are accepted, as `Priya S.`, `Priya Sharma`, or `Priya Nair`.
- **FR-E13** Identity of a person across notes is their **email address** when available, otherwise normalised full name. Two different people sharing a first name are therefore never merged into one owner.
- **FR-E14** A first name appearing in the text but with no matching attendee → unassigned plus warning.
- **FR-E15** `list --owner` and `followup <owner>` accept full name or email. A bare first name works only if unique across stored owners. Otherwise the command lists the candidates (name + email) and exits non-zero without acting.

### 7.4 Malformed notes

A note is **malformed** and skipped when any of the following holds:

- front matter is missing or is invalid YAML,
- `date` is missing or not a valid date,
- `attendees` is missing or empty,
- the file is unreadable, empty, or not valid UTF-8.

Requirements:

- **FR-E16** A malformed note is skipped **entirely**, so no partial items from it are stored, and the failure is reported with filename and reason.
- **FR-E17** The run continues to the remaining files and exits `0` (FR-I6).
- **FR-E18** An individual line that looks like an action item but cannot be understood is **not a malformed note**. The item is still stored, with its raw text as the task, unassigned and undated, plus a warning.
- **FR-E19** Warnings and skip reports are written to stderr and included in the end-of-run summary. A stack trace is never shown to the user in normal operation (`--verbose` may show details).

## 8. Non-Functional Requirements

| ID | Requirement |
|---|---|
| NFR-1 | **Platform:** Python 3.10+, standard library preferred (`argparse`, `sqlite3`, `datetime`). Minimal third-party dependencies (YAML parsing only if no stdlib solution is practical). Runs on Windows, macOS and Linux. |
| NFR-2 | **Reliability:** no unhandled exception on any input file. Ingest of one folder is atomic per file. A crash mid-run must not corrupt the DB (SQLite transactions). |
| NFR-3 | **Idempotency:** repeating `ingest` on unchanged input yields no change. |
| NFR-4 | **Performance:** ingest 500 notes (≈ 5,000 items) in under 10 seconds. `list` returns in under 1 second. |
| NFR-5 | **Safety:** no email is ever sent (FR-F4). The tool never modifies or deletes the source notes. |
| NFR-6 | **Privacy:** data stays local. The only external call is Gmail draft creation, containing only the follow-up body for that owner. |
| NFR-7 | **Usability:** `--help` for every command, clear human-readable errors, consistent exit codes (`0` success, `1` runtime error, `2` bad usage/ambiguous input). |
| NFR-8 | **Determinism:** "today" comes from the system clock but is injectable (e.g. `--today` or env var) so overdue logic is testable. |
| NFR-9 | **Testability:** parser, date resolver, dedup and owner-resolver are pure functions with unit tests. The Gmail layer is behind a thin interface so it can be mocked. |
| NFR-10 | **Timezone:** dates are date-only in the system's local timezone. No time-of-day semantics. |

## 9. External Interface — Gmail MCP Connector

- **IR-1** Draft creation uses the Gmail MCP connector's create-draft operation only.
- **IR-2** The connector requires the user to be authenticated. Authentication failure is surfaced per FR-F8.
- **IR-3** Draft fields: `to` (owner email), `subject` (`Action items follow-up — <Owner first name> — <today>`), `body` (plain text, FR-F2).
- **IR-4** The exact connector tool names and parameters are to be confirmed during design (Q-8).

## 10. Acceptance Criteria (high-level)

| # | Scenario | Expected |
|---|---|---|
| AC-1 | Ingest folder with 3 valid notes | Items stored with owner, task, resolved due date, source; summary printed |
| AC-2 | Same item in two notes | One record; `also_seen_in` lists the second note |
| AC-3 | "Priya to send quote by Friday", meeting Mon 2026-10-12 | Due date = 2026-10-16 |
| AC-4 | Item with no owner / no date | Stored; shown as unassigned / `—`; not overdue |
| AC-5 | Two Priyas attend, text says only "Priya" | Stored unassigned, flagged ambiguous, listed in summary |
| AC-6 | Note with no front matter | Skipped, reported with reason; other notes ingested; exit 0 |
| AC-7 | `list --status overdue` | Only open items with due date before today |
| AC-8 | `list --owner X --due-before D` | AND of both filters |
| AC-9 | `done 12` | Item 12 → done; excluded from later lists/follow-ups |
| AC-10 | `followup Rahul` | One Gmail draft with Overdue and Open sections; nothing sent |
| AC-11 | `followup Priya` (ambiguous) | Candidates listed, no draft, exit 2 |
| AC-12 | Re-run ingest on same folder | No duplicates, done items stay done |
| AC-13 | Any code path | No call to a send operation (verified by test) |

## 11. Assumptions and Open Questions

Items marked **Assumed** were decided by the analyst to keep moving. Please confirm or correct them.

| # | Topic | Current position |
|---|---|---|
| Q-1 | The `ingest` and `followup` lines in the RTF are truncated | **Assumed** as written in §6 |
| Q-2 | Items with a bare `- [ ]` and no owner pattern (e.g. "Update the doc") | **Assumed** unassigned, kept |
| Q-3 | Recursive folder scan | **Assumed** no (top level only) |
| Q-4 | If a note later shows `[ ]` for an item previously `[x]` or marked done via CLI | **Assumed** stays done (CLI is source of truth) |
| Q-5 | `followup` with no argument / `--all` for every owner | **Assumed** owner argument required. `--all` could be added later |
| Q-6 | Owner with no email: skip vs. empty-recipient draft | **Assumed** skip and report by default, `--no-recipient` opt-in |
| Q-7 | Fuzzy duplicate detection (reworded tasks) | **Assumed** out of scope for v1 |
| Q-8 | Exact Gmail MCP tool names/params, and where the tool runs relative to the MCP client | **Open**: confirm in design |
| Q-9 | Should a due date that changes between meetings update the item? | **Assumed** yes, keep the latest |
| Q-10 | Are meeting dates ever in the future relative to today? | **Assumed** allowed, no validation error |

## 12. Decisions Captured from Stakeholder

| Question | Decision |
|---|---|
| Note format | YAML front matter (`date`, `attendees`) + free-form body |
| Owner email source | Attendee list in the note, as `Name <email>` |
| Storage | SQLite file |
| Language | Python |

## 13. Glossary

- **Action item:** a `- [ ]` / `- [x]` line in a note.
- **Owner:** the person responsible, resolved to an attendee.
- **Overdue:** open item whose due date is before today.
- **Draft:** an unsent Gmail message saved for human review.
