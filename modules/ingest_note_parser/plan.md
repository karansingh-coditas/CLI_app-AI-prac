# ingest_note_parser — Plan

## Approach
Split on the front-matter fences by hand, feed the block to `yaml.safe_load`, validate fields, then scan the body with one compiled regex.

## Design decisions
- **PyYAML over a hand-rolled parser:** names like `"Doe, Jane" <j@x.com>` and quoting rules are error-prone to hand-parse. This is the only third-party dependency in the project (allowed by NFR-1 as there is no practical stdlib YAML).
- **`safe_load` only**, to avoid arbitrary object construction from untrusted notes.
- **Attendee parsing** with regex `^(?P<name>[^<]+?)\s*(?:<(?P<email>[^>]+)>)?$`.
- Line numbers kept so warnings from later modules can point at the file line.
- BOM tolerated (`utf-8-sig` handled by runner; parser also strips a leading `﻿`).

## Steps
1. Front-matter splitter (fence detection, CRLF-safe).
2. YAML load + type checks.
3. `date` validation, `attendees` parsing into `Person`s.
4. Body regex for items, with original line numbers.
5. Tests, including a fixtures folder of good/bad notes shared with `ingest_runner` tests.

## Risks
- A YAML date unquoted becomes `datetime.date`; quoted becomes `str`. Handle both.
- A checkbox inside a code fence would count as an item. Accepted for v1 (documented ceiling).
- Windows line endings: normalise `\r\n` before processing.

## Definition of done
All `test-cases.md` pass; module only ever raises `MalformedNote`.
