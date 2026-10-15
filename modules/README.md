# actiontrack — Module Breakdown

Derived from `../requirement.md`. Each module folder holds `spec.md`, `plan.md`, `tasks.md`, `test-cases.md`.
Each module is **one Python file**: `src/actiontrack/<module_name>.py`. Tests: `tests/test_<module_name>.py`.

## Naming convention

Related modules share a prefix: `<family>_<feature>`.

| Family | Purpose | Modules |
|---|---|---|
| `core_` | Shared contracts and persistence | `core_models`, `core_store` |
| `ingest_` | Everything for `actiontrack ingest` | `ingest_note_parser`, `ingest_owner_resolver`, `ingest_date_resolver`, `ingest_dedup`, `ingest_runner` |
| `track_` | Reading / updating stored items (`list`, `done`) | `track_owner_lookup`, `track_list`, `track_done` |
| `followup_` | Everything for `actiontrack followup` | `followup_compose`, `followup_gmail_draft`, `followup_runner` |
| `cli_` | Entry point and wiring | `cli_app` |

## Loose-coupling rules

1. **Pure leaf modules** (`ingest_note_parser`, `ingest_owner_resolver`, `ingest_date_resolver`, `ingest_dedup`, `track_owner_lookup`, `followup_compose`) import **only `core_models`**. No I/O, no database, no clock. They can be built and tested alone.
2. **Only `core_store` touches SQLite.** Only `followup_gmail_draft` touches Gmail. Only `ingest_note_parser` and `ingest_runner` touch note files.
3. **Runners** (`ingest_runner`, `followup_runner`, `track_list`, `track_done`) orchestrate. They receive their collaborators as arguments (store, gateway, today). They never import another family's runner.
4. **Families do not import each other's internals.** `ingest_*` never imports `followup_*` or `track_*`, and so on. The shared surface is `core_models` + `core_store`.
5. **`cli_app` is the only place** where concrete classes are wired together.
6. Cross-module data moves only as `core_models` dataclasses. No module reads another's private state.

## Dependency graph

```
                      cli_app
        ┌───────────────┼──────────────────┬───────────────┐
        ▼               ▼                  ▼               ▼
  ingest_runner     track_list         track_done    followup_runner
   │ │ │ │ │          │   │               │          │   │   │   │
   │ │ │ │ └─► ingest_dedup                │          │   │   │   └─► followup_gmail_draft
   │ │ │ └───► ingest_date_resolver        │          │   │   └─────► followup_compose
   │ │ └─────► ingest_owner_resolver       │          │   └─────────► track_owner_lookup
   │ └───────► ingest_note_parser          │          │
   └──┬────────────────┬──────────────────┴──────────┘
      ▼                ▼
  core_store ──► core_models  ◄── (every module)
```

`track_list` and `followup_runner` also use `track_owner_lookup` (one-way, pure function).
`followup_runner` uses `followup_gmail_draft` only through the `DraftGateway` protocol.

## Shared contracts (defined once, in `core_models`)

`Person`, `RawItemLine`, `Note`, `Item`, `Issue`, `Draft`, `DraftResult`, `MalformedNote`, `AppError`, exit codes, `is_overdue()`, `resolve_today()`. See `core_models/spec.md`.

## Suggested build order

1. `core_models` → 2. `core_store`
3. In parallel (all independent): `ingest_note_parser`, `ingest_owner_resolver`, `ingest_date_resolver`, `ingest_dedup`, `track_owner_lookup`, `followup_compose`, `followup_gmail_draft`
4. `ingest_runner`, `track_list`, `track_done`, `followup_runner`
5. `cli_app` → end-to-end acceptance tests

## Requirement traceability

| Requirement | Module(s) |
|---|---|
| FR-N1, N2, N3, E16 | `ingest_note_parser` |
| FR-N4, I1, I4, I5, I6, E9, E17 | `ingest_runner` |
| FR-P1, E10, E11, E12, E14 | `ingest_owner_resolver` |
| FR-P2 | `ingest_date_resolver` |
| FR-P3 | `ingest_note_parser` (flag) + `ingest_runner` (status) |
| FR-I2, I3 (storage), NFR-2 (atomic) | `core_store` |
| FR-I3 (no dupes), I7, E1–E5 | `ingest_dedup` (+ `ingest_runner`) |
| FR-E13 (identity) | `core_models` (`Person.key`) |
| FR-E15 | `track_owner_lookup` |
| FR-L1–L5, E7 (list unassigned), E8 | `track_list`, `core_models` (`is_overdue`) |
| FR-D1–D4 | `track_done` |
| FR-F1, F2, E4 | `followup_compose` |
| FR-F3, F4, F8, F10, IR-1–IR-4 | `followup_gmail_draft` |
| FR-F5, F6, F7, F9, E7 (count) | `followup_runner` |
| FR-E18 | `ingest_owner_resolver` + `ingest_date_resolver` + `ingest_runner` |
| FR-E19, NFR-7, NFR-8 | `cli_app`, `core_models` |
| NFR-5 | `followup_gmail_draft`, `ingest_runner` (read-only on notes) |

## Acceptance-criteria coverage

| AC | Verified in |
|---|---|
| AC-1, 2, 4, 5, 6, 12 | `ingest_runner/test-cases.md` (end-to-end) |
| AC-3 | `ingest_date_resolver/test-cases.md` |
| AC-7, 8 | `track_list/test-cases.md` |
| AC-9 | `track_done/test-cases.md` |
| AC-10, 11 | `followup_runner/test-cases.md` |
| AC-13 | `followup_gmail_draft/test-cases.md` |
| All | `cli_app/test-cases.md` (smoke across commands) |

## Project layout

```
src/actiontrack/        one .py per module
tests/                  test_<module>.py, plus fixtures/notes/*.md
pyproject.toml          console script: actiontrack = actiontrack.cli_app:main
```
