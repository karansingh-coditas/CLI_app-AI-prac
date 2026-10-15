"""Entry point: argument parsing, wiring concrete classes together, printing, exit codes."""
from __future__ import annotations

import argparse
import contextlib
import os
import sys
import traceback
from datetime import date, datetime
from typing import Callable, Mapping, Sequence, TextIO

from .core_models import AppError, OK, RUNTIME_ERROR, USAGE_ERROR, resolve_today
from .core_store import Store, default_db_path
from .followup_gmail_draft import DraftGateway, DryRunGateway, McpGmailGateway
from .followup_runner import run_followup
from .ingest_runner import format_report, run_ingest
from .track_done import mark_done
from .track_list import format_table, list_items


class _Safe:
    """Text stream that degrades to replacement characters instead of raising UnicodeEncodeError."""

    def __init__(self, stream: TextIO):
        self._s = stream

    def write(self, text: str) -> int:
        try:
            return self._s.write(text)
        except UnicodeEncodeError:
            enc = getattr(self._s, "encoding", None) or "ascii"
            return self._s.write(text.encode(enc, "replace").decode(enc))

    def flush(self) -> None:
        self._s.flush()


def _iso_date(s: str) -> date:
    try:
        return date.fromisoformat(s)
    except ValueError:
        raise argparse.ArgumentTypeError(f"invalid date {s!r} (expected YYYY-MM-DD)") from None


def _parser() -> argparse.ArgumentParser:
    def add_globals(p: argparse.ArgumentParser, in_subcommand: bool) -> None:
        kw = {"default": argparse.SUPPRESS} if in_subcommand else {}  # let the top-level value stand
        p.add_argument("--db", metavar="PATH", **kw,
                       help="SQLite file (default: $ACTIONTRACK_DB, else ./actiontrack.db)")
        p.add_argument("--today", metavar="YYYY-MM-DD", **kw,
                       help="treat this date as today (default: $ACTIONTRACK_TODAY, else system date)")
        p.add_argument("--verbose", action="store_true", **kw, help="show tracebacks and connector details")

    top = argparse.ArgumentParser(prog="actiontrack", description="Track action items from meeting notes.")
    add_globals(top, False)
    common = argparse.ArgumentParser(add_help=False)
    add_globals(common, True)
    sub = top.add_subparsers(dest="command", required=True, metavar="<command>")

    p = sub.add_parser("ingest", parents=[common], help="read a folder of .md notes into the database")
    p.add_argument("folder")

    p = sub.add_parser("list", parents=[common], help="list items (overdue first, undated last)")
    p.add_argument("--owner", metavar="NAME", help="full name, email, first name if unique, or 'unassigned'")
    p.add_argument("--status", choices=["open", "done", "overdue"],
                   help="note: 'open' includes overdue items; 'overdue' selects only the overdue subset")
    p.add_argument("--due-before", type=_iso_date, metavar="YYYY-MM-DD",
                   help="only items due before this date (undated items excluded)")

    p = sub.add_parser("done", parents=[common], help="mark an item done")
    p.add_argument("id", type=int)

    p = sub.add_parser("followup", parents=[common], help="create a Gmail draft (never sends) for one owner")
    p.add_argument("owner")
    p.add_argument("--no-recipient", action="store_true", help="create the draft even if the owner has no email")
    p.add_argument("--dry-run", action="store_true", help="print the draft instead of creating it")
    return top


def main(argv: Sequence[str] | None = None, env: Mapping[str, str] | None = None,
         stdout: TextIO | None = None, stderr: TextIO | None = None,
         gateway_factory: Callable[[], DraftGateway] | None = None) -> int:
    env = os.environ if env is None else env
    out, err = _Safe(stdout or sys.stdout), _Safe(stderr or sys.stderr)
    try:
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            args = _parser().parse_args(argv)
    except SystemExit as e:  # argparse: --help (0) or usage error (2)
        return e.code if isinstance(e.code, int) else USAGE_ERROR
    try:
        today = resolve_today(args.today, env)
        store = Store(default_db_path(args.db, env))
        with contextlib.closing(store):
            return _COMMANDS[args.command](args, store, today, env, out, err, gateway_factory)
    except AppError as e:
        print(f"error: {e.message}", file=err)
        return e.exit_code
    except Exception as e:
        print(f"error: unexpected failure ({type(e).__name__}); re-run with --verbose", file=err)
        if args.verbose:
            traceback.print_exc(file=err)
        return RUNTIME_ERROR


def _ingest(args, store, today, env, out, err, _gf) -> int:
    report = run_ingest(args.folder, store, datetime.now())
    print(format_report(report), file=out)
    for i in report.files_skipped:
        print(f"skipped: {i.file} — {i.message}", file=err)
    for i in report.issues:
        print(f"warning: {i.file}{':' + str(i.line) if i.line else ''} — {i.message}", file=err)
    return OK


def _list(args, store, today, env, out, err, _gf) -> int:
    r = list_items(store, today, args.owner, args.status, args.due_before)
    if r.status == "ambiguous_owner":
        names = "\n".join(f"  {p.name} <{p.email}>" if p.email else f"  {p.name}" for p in r.candidates)
        print(f"error: '{args.owner}' matches several owners:\n{names}\nRetype with the full name or email.", file=err)
        return USAGE_ERROR
    if r.status == "owner_not_found":
        print(f"error: No owner matches '{args.owner}'", file=err)
        return USAGE_ERROR
    print(format_table(r.items, today), file=out)
    return OK


def _done(args, store, today, env, out, err, _gf) -> int:
    r = mark_done(store, args.id, datetime.now())
    if r.outcome == "not_found":
        print(f"error: {r.message}", file=err)
        return USAGE_ERROR
    print(r.message, file=out)
    return OK


def _followup(args, store, today, env, out, err, gateway_factory) -> int:
    if args.dry_run:
        gateway = DryRunGateway(out)
    elif gateway_factory:
        gateway = gateway_factory()
    else:  # constructed only here, so other commands never need Gmail setup
        gateway = McpGmailGateway(verbose=args.verbose, env=env)
    o = run_followup(args.owner, store, gateway, today, args.no_recipient)
    print(o.message if o.exit_code == OK else f"error: {o.message}", file=out if o.exit_code == OK else err)
    return o.exit_code


_COMMANDS = {"ingest": _ingest, "list": _list, "done": _done, "followup": _followup}
